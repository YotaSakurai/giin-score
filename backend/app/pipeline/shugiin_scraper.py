"""衆議院議案スクレイピング

衆議院Webサイトから法案一覧・法案詳細・提出者情報を取得する。
"""
import logging
import re
import time
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.models.bill import Bill, BillSponsor
from app.models.pipeline import PipelineRun
from app.models.session import DietSession
from app.pipeline.member_master import normalize_name, find_or_create_member

logger = logging.getLogger(__name__)

BASE_URL = "https://www.shugiin.go.jp"
USER_AGENT = "GiinScore/0.1 (Data Pipeline)"

# テーブルcaptionから法案種別へのマッピング
CAPTION_TO_KIND = {
    "閣法の一覧": "閣法",
    "衆法の一覧": "衆法",
    "参法の一覧": "参法",
}

# 審議状況テキストからstatusへのマッピング
STATUS_MAP = {
    "成立": "成立",
    "未了": "廃案",
    "審議中": "審議中",
    "衆議院で閉会中審査": "継続",
    "参議院で閉会中審査": "継続",
    "本院可決": "審議中",
    "本院議了": "成立",
}


def scrape_bills_list(db: Session, session_number: int) -> int:
    """衆議院サイトから法案一覧をスクレイピングしてbillsテーブルに投入する。"""
    pipeline_run = PipelineRun(
        pipeline_name="shugiin_bills_list",
        session_number=session_number,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(pipeline_run)
    db.commit()

    total_processed = 0

    try:
        list_url = f"{BASE_URL}/internet/itdb_gian.nsf/html/gian/kaiji{session_number}.htm"

        with httpx.Client(
            timeout=30.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        ) as client:
            time.sleep(settings.kokkai_api_rate_limit)
            resp = client.get(list_url)
            resp.raise_for_status()
            resp.encoding = _detect_encoding(resp)

            soup = BeautifulSoup(resp.text, "lxml")
            if not _health_check(soup):
                logger.error("HTML structure changed - health check failed")
                pipeline_run.status = "failed"
                pipeline_run.error_message = "HTML structure health check failed"
                pipeline_run.finished_at = datetime.utcnow()
                db.commit()
                return 0

            # 会期を取得または作成
            diet_session = db.query(DietSession).filter_by(
                session_number=session_number
            ).first()
            if not diet_session:
                diet_session = DietSession(
                    session_number=session_number, kind="通常"
                )
                db.add(diet_session)
                db.flush()

            # 各テーブル(閣法/衆法/参法)を処理
            for table in soup.find_all("table"):
                caption = table.find("caption")
                if not caption:
                    continue
                caption_text = caption.get_text(strip=True)
                bill_kind = CAPTION_TO_KIND.get(caption_text)
                if not bill_kind:
                    continue

                logger.info(f"Processing {caption_text}")
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) < 4:
                        continue

                    submitted_session = cells[0].get_text(strip=True)
                    bill_number = cells[1].get_text(strip=True)
                    title = cells[2].get_text(strip=True)
                    status_text = cells[3].get_text(strip=True)

                    if not title:
                        continue

                    # この会期に提出された法案のみ取得
                    try:
                        sub_session = int(submitted_session)
                    except (ValueError, TypeError):
                        continue

                    if sub_session != session_number:
                        continue

                    # ステータスの正規化
                    status = _normalize_status(status_text)

                    # 提出者種別の推定
                    proposer_type = "cabinet" if bill_kind == "閣法" else "member"

                    # 重複チェック
                    existing = (
                        db.query(Bill)
                        .filter_by(
                            session_id=diet_session.id,
                            bill_kind=bill_kind,
                            title=title,
                        )
                        .first()
                    )
                    if existing:
                        # ステータスだけ更新
                        if status and existing.status != status:
                            existing.status = status
                        continue

                    bill = Bill(
                        session_id=diet_session.id,
                        bill_kind=bill_kind,
                        bill_number=bill_number if bill_number else None,
                        title=title,
                        status=status,
                        result=status if status in ("成立", "廃案") else None,
                        proposer_type=proposer_type,
                    )
                    db.add(bill)
                    total_processed += 1

                    if total_processed % 100 == 0:
                        db.commit()

        db.commit()
        pipeline_run.status = "completed"
        pipeline_run.records_processed = total_processed
        pipeline_run.finished_at = datetime.utcnow()
        db.commit()
        logger.info(
            f"Completed: {total_processed} bills from Shugiin list for session {session_number}"
        )

    except Exception as e:
        pipeline_run.status = "failed"
        pipeline_run.error_message = str(e)
        pipeline_run.finished_at = datetime.utcnow()
        db.commit()
        logger.error(f"Shugiin bills list scraper failed: {e}")
        raise

    return total_processed


def _normalize_status(text: str) -> str | None:
    """審議状況テキストをステータスに正規化する。"""
    text = text.strip()
    if not text:
        return None

    # 完全一致
    if text in STATUS_MAP:
        return STATUS_MAP[text]

    # 部分一致
    if "成立" in text:
        return "成立"
    if "可決" in text:
        return "成立"
    if "修正" in text and "可決" in text:
        return "成立"
    if "否決" in text:
        return "否決"
    if "未了" in text:
        return "廃案"
    if "閉会中審査" in text:
        return "継続"
    if "継続" in text:
        return "継続"
    if "撤回" in text:
        return "撤回"

    return "審議中"


def scrape_bills(db: Session, session_number: int) -> int:
    """衆議院の議案情報をスクレイピングする。"""
    pipeline_run = PipelineRun(
        pipeline_name="shugiin_bills",
        session_number=session_number,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(pipeline_run)
    db.commit()

    total_processed = 0

    try:
        # 議案一覧ページ
        list_url = f"{BASE_URL}/internet/itdb_gian.nsf/html/gian/kaiji{session_number}.htm"

        with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            time.sleep(settings.kokkai_api_rate_limit)
            resp = client.get(list_url)
            resp.raise_for_status()
            resp.encoding = _detect_encoding(resp)

            soup = BeautifulSoup(resp.text, "lxml")
            if not _health_check(soup):
                logger.error("HTML structure changed - health check failed")
                pipeline_run.status = "failed"
                pipeline_run.error_message = "HTML structure health check failed"
                pipeline_run.finished_at = datetime.utcnow()
                db.commit()
                return 0

            bill_links = _extract_bill_links(soup)
            logger.info(f"Found {len(bill_links)} bill pages for session {session_number}")

            for link in bill_links:
                try:
                    time.sleep(settings.kokkai_api_rate_limit)
                    if _scrape_bill_detail(db, client, session_number, link):
                        total_processed += 1
                except Exception as e:
                    logger.warning(f"Failed to scrape {link}: {e}")

                if total_processed % 100 == 0 and total_processed > 0:
                    db.commit()

        db.commit()
        pipeline_run.status = "completed"
        pipeline_run.records_processed = total_processed
        pipeline_run.finished_at = datetime.utcnow()
        db.commit()
        logger.info(f"Completed: {total_processed} bills for session {session_number}")

    except Exception as e:
        pipeline_run.status = "failed"
        pipeline_run.error_message = str(e)
        pipeline_run.finished_at = datetime.utcnow()
        db.commit()
        logger.error(f"Shugiin scraper failed: {e}")
        raise

    return total_processed


def _detect_encoding(resp: httpx.Response) -> str:
    content_type = resp.headers.get("content-type", "")
    if "euc-jp" in content_type.lower():
        return "euc-jp"
    if "shift_jis" in content_type.lower():
        return "shift_jis"
    return "utf-8"


def _health_check(soup: BeautifulSoup) -> bool:
    return soup.find("table") is not None or soup.find("a") is not None


def _extract_bill_links(soup: BeautifulSoup) -> list[str]:
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "gian_honbun" in href or "gian" in href:
            if href.startswith("http"):
                links.append(href)
            elif href.startswith("/"):
                links.append(f"{BASE_URL}{href}")
    return links


def _scrape_bill_detail(db: Session, client: httpx.Client, session_number: int, url: str) -> bool:
    """個別法案の詳細ページをスクレイピングする。"""
    resp = client.get(url)
    resp.raise_for_status()
    resp.encoding = _detect_encoding(resp)

    soup = BeautifulSoup(resp.text, "lxml")

    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        return False

    # 法案タイトル
    title = ""
    title_elem = soup.find("h3") or soup.find("h2")
    if title_elem:
        title = title_elem.get_text(strip=True)

    if not title:
        return False

    # 提出者情報を抽出
    sponsors_text = ""
    for th in soup.find_all(["th", "td"]):
        if "提出者" in th.get_text():
            next_td = th.find_next_sibling("td")
            if next_td:
                sponsors_text = next_td.get_text(strip=True)
            break

    # billを検索して提出者を紐づけ
    bill = db.query(Bill).filter_by(session_id=diet_session.id, title=title).first()
    if not bill:
        return False

    # 提出者をパース
    if sponsors_text:
        names = _parse_sponsor_names(sponsors_text)
        for i, name in enumerate(names):
            member = find_or_create_member(
                db,
                name=normalize_name(name),
                chamber="representatives",
            )
            sponsor_type = "primary" if i == 0 else "co-sponsor"

            existing = (
                db.query(BillSponsor)
                .filter_by(bill_id=bill.id, member_id=member.id)
                .first()
            )
            if not existing:
                sponsor = BillSponsor(
                    bill_id=bill.id,
                    member_id=member.id,
                    sponsor_type=sponsor_type,
                )
                db.add(sponsor)

    return True


def _parse_sponsor_names(text: str) -> list[str]:
    """提出者テキストから議員名リストを抽出する。"""
    # 「内閣」などの場合はスキップ
    if "内閣" in text:
        return []

    # 句読点やスペースで分割
    names = re.split(r"[、，,\s　]+", text)
    # 空文字列やノイズを除去
    return [n.strip() for n in names if n.strip() and len(n.strip()) >= 2]
