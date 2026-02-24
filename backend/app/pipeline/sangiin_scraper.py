"""参議院投票データスクレイピング

参議院Webサイトの投票結果ページから個別議員の投票記録を取得する。
"""

import logging
import re
import time
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.models.bill import Bill
from app.models.pipeline import PipelineRun
from app.models.session import DietSession
from app.models.vote import VoteRecord, VoteResult
from app.pipeline.member_master import find_or_create_member, normalize_name
from app.pipeline.utils import USER_AGENT, detect_encoding, health_check

logger = logging.getLogger(__name__)

BASE_URL = "https://www.sangiin.go.jp"


def scrape_votes(db: Session, session_number: int) -> int:
    """参議院の投票結果を取得する。"""
    pipeline_run = PipelineRun(
        pipeline_name="sangiin_votes",
        session_number=session_number,
        status="running",
        started_at=datetime.now(UTC),
    )
    db.add(pipeline_run)
    db.commit()

    total_processed = 0

    try:
        vote_list_url = f"{BASE_URL}/japanese/touhyoulist/{session_number}/vote_ind.htm"

        with httpx.Client(
            timeout=30.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        ) as client:
            time.sleep(settings.kokkai_api_rate_limit)
            resp = client.get(vote_list_url)
            resp.raise_for_status()
            resp.encoding = detect_encoding(resp)

            soup = BeautifulSoup(resp.text, "lxml")
            if not health_check(soup):
                logger.error("HTML structure changed - health check failed")
                pipeline_run.status = "failed"
                pipeline_run.error_message = "HTML structure health check failed"
                pipeline_run.finished_at = datetime.now(UTC)
                db.commit()
                return 0

            vote_links = _extract_vote_links(soup, vote_list_url)
            logger.info(f"Found {len(vote_links)} vote pages for session {session_number}")

            for link in vote_links:
                try:
                    time.sleep(settings.kokkai_api_rate_limit)
                    count = _scrape_vote_page(db, client, session_number, link)
                    total_processed += count
                except Exception as e:
                    logger.warning(f"Failed to scrape {link}: {e}")

        db.commit()
        pipeline_run.status = "completed"
        pipeline_run.records_processed = total_processed
        pipeline_run.finished_at = datetime.now(UTC)
        db.commit()
        logger.info(f"Completed: {total_processed} vote records for session {session_number}")

    except Exception as e:
        pipeline_run.status = "failed"
        pipeline_run.error_message = str(e)
        pipeline_run.finished_at = datetime.now(UTC)
        db.commit()
        logger.error(f"Sangiin scraper failed: {e}")
        raise

    return total_processed


def _extract_vote_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """投票結果ページへのリンクを抽出する。"""
    # base_url から相対パスを解決するためのディレクトリ部分
    base_dir = base_url.rsplit("/", 1)[0]
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # 個別投票結果ページ（例: 213-0619-v001.htm）のパターン
        if href.endswith(".htm") and "-v" in href:
            if href.startswith("http"):
                links.append(href)
            elif href.startswith("/"):
                links.append(f"{BASE_URL}{href}")
            else:
                links.append(f"{base_dir}/{href}")
    return links


def _scrape_vote_page(db: Session, client: httpx.Client, session_number: int, url: str) -> int:
    """個別の投票結果ページをスクレイピングする。"""
    resp = client.get(url)
    resp.raise_for_status()
    resp.encoding = detect_encoding(resp)

    soup = BeautifulSoup(resp.text, "lxml")
    body_text = soup.get_text()

    # 議案名を取得（dl/dd構造から）
    bill_title = ""
    for dt in soup.find_all("dt"):
        if "案件名" in dt.get_text():
            dd = dt.find_next_sibling("dd")
            if dd:
                bill_title = dd.get_text(strip=True)
                # 「日程第N　」プレフィクスを除去
                bill_title = re.sub(r"^日程第\d+\s*", "", bill_title)
                # 「（内閣提出、衆議院送付）」などのサフィックスを除去
                bill_title = re.sub(r"（[^）]*提出[^）]*）$", "", bill_title)
                bill_title = bill_title.strip()
            break

    if not bill_title:
        # フォールバック: h2/h3からタイトル取得
        title_elem = soup.find("h2") or soup.find("h3")
        if title_elem:
            bill_title = title_elem.get_text(strip=True)

    if not bill_title:
        return 0

    # 会期とbillを関連付け
    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        return 0

    # タイトル部分一致で法案を検索
    bill = (
        db.query(Bill)
        .filter(
            Bill.session_id == diet_session.id,
            Bill.title.contains(bill_title[:30]),
        )
        .first()
    )

    # 結果を判定
    result_text = None
    if "可決" in body_text:
        result_text = "可決"
    elif "否決" in body_text:
        result_text = "否決"

    if not bill:
        logger.debug(f"Bill not found for: {bill_title[:50]}")
        return 0

    # 既存VoteResultチェック
    existing = db.query(VoteResult).filter_by(bill_id=bill.id, chamber="councillors").first()
    if existing:
        return 0

    # 集計結果の取得（テーブルがある場合 = 記名投票）
    ayes = 0
    nays = 0
    tables = soup.find_all("table")
    for table in tables:
        text = table.get_text()
        if "賛成" in text and "反対" in text:
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                for i, cell in enumerate(cells):
                    t = cell.get_text(strip=True)
                    if "賛成" in t and i + 1 < len(cells):
                        try:
                            ayes = int(cells[i + 1].get_text(strip=True).replace(",", ""))
                        except ValueError:
                            pass
                    if "反対" in t and i + 1 < len(cells):
                        try:
                            nays = int(cells[i + 1].get_text(strip=True).replace(",", ""))
                        except ValueError:
                            pass

    vote_result = VoteResult(
        bill_id=bill.id,
        chamber="councillors",
        ayes=ayes,
        nays=nays,
        result=result_text,
    )
    db.add(vote_result)
    db.flush()

    # 個別議員の投票記録を取得（記名投票の場合のみ）
    count = 0
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 2:
                name_text = cells[0].get_text(strip=True)
                vote_text = cells[-1].get_text(strip=True)

                if not name_text or name_text in ("氏名", "議員名"):
                    continue

                vote_value = _parse_vote(vote_text)
                if not vote_value:
                    continue

                member = find_or_create_member(
                    db,
                    name=normalize_name(name_text),
                    chamber="councillors",
                )

                record = VoteRecord(
                    vote_result_id=vote_result.id,
                    member_id=member.id,
                    vote=vote_value,
                )
                db.add(record)
                count += 1

    # 起立採決の場合もVoteResultは1件としてカウント
    return max(count, 1) if result_text else count


def _parse_vote(text: str) -> str | None:
    """投票テキストをaye/nay/abstain/absentに変換する。"""
    text = text.strip()
    if text in ("賛成", "○", "〇"):
        return "aye"
    if text in ("反対", "×", "✕"):
        return "nay"
    if text in ("棄権",):
        return "abstain"
    if text in ("欠席",):
        return "absent"
    return None
