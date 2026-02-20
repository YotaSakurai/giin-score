"""衆議院議案スクレイピング

衆議院Webサイトから法案詳細・提出者情報を取得する。
"""
import logging
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
    import re
    names = re.split(r"[、，,\s　]+", text)
    # 空文字列やノイズを除去
    return [n.strip() for n in names if n.strip() and len(n.strip()) >= 2]
