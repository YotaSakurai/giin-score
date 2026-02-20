"""参議院投票データスクレイピング

参議院Webサイトの投票結果ページから個別議員の投票記録を取得する。
"""
import logging
import time
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.models.bill import Bill
from app.models.member import Member
from app.models.pipeline import PipelineRun
from app.models.session import DietSession
from app.models.vote import VoteRecord, VoteResult
from app.pipeline.member_master import normalize_name, find_or_create_member

logger = logging.getLogger(__name__)

BASE_URL = "https://www.sangiin.go.jp"
USER_AGENT = "GiinScore/0.1 (Data Pipeline)"


def scrape_votes(db: Session, session_number: int) -> int:
    """参議院の投票結果を取得する。"""
    pipeline_run = PipelineRun(
        pipeline_name="sangiin_votes",
        session_number=session_number,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(pipeline_run)
    db.commit()

    total_processed = 0

    try:
        vote_list_url = f"{BASE_URL}/japanese/joho1/kousei/vote/kaiki/{session_number}/vote_list.htm"

        with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
            time.sleep(settings.kokkai_api_rate_limit)
            resp = client.get(vote_list_url)
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

            vote_links = _extract_vote_links(soup)
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
        pipeline_run.finished_at = datetime.utcnow()
        db.commit()
        logger.info(f"Completed: {total_processed} vote records for session {session_number}")

    except Exception as e:
        pipeline_run.status = "failed"
        pipeline_run.error_message = str(e)
        pipeline_run.finished_at = datetime.utcnow()
        db.commit()
        logger.error(f"Sangiin scraper failed: {e}")
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
    """HTML構造が期待通りかチェックする。"""
    # テーブルまたはリンクが存在することを確認
    return soup.find("table") is not None or soup.find("a") is not None


def _extract_vote_links(soup: BeautifulSoup) -> list[str]:
    """投票結果ページへのリンクを抽出する。"""
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "vote_ind" in href or "vote_result" in href:
            if href.startswith("http"):
                links.append(href)
            else:
                links.append(f"{BASE_URL}{href}" if href.startswith("/") else f"{BASE_URL}/{href}")
    return links


def _scrape_vote_page(db: Session, client: httpx.Client, session_number: int, url: str) -> int:
    """個別の投票結果ページをスクレイピングする。"""
    resp = client.get(url)
    resp.raise_for_status()
    resp.encoding = _detect_encoding(resp)

    soup = BeautifulSoup(resp.text, "lxml")

    # 議案名を取得
    title_elem = soup.find("h2") or soup.find("h3") or soup.find("title")
    bill_title = title_elem.get_text(strip=True) if title_elem else "不明"

    # 会期とbillを関連付け
    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        return 0

    bill = db.query(Bill).filter_by(session_id=diet_session.id, title=bill_title).first()

    # 集計結果の取得
    ayes = 0
    nays = 0
    result_text = None
    tables = soup.find_all("table")
    for table in tables:
        text = table.get_text()
        if "賛成" in text and "反対" in text:
            # 賛否数の抽出を試みる
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

    if ayes > nays:
        result_text = "可決"
    elif nays > ayes:
        result_text = "否決"

    if not bill:
        # billがなければVoteResultだけ作成（bill_idは後でリンク可能）
        logger.info(f"Bill not found for: {bill_title}")
        return 0

    vote_result = VoteResult(
        bill_id=bill.id,
        chamber="councillors",
        ayes=ayes,
        nays=nays,
        result=result_text,
    )
    db.add(vote_result)
    db.flush()

    # 個別議員の投票記録を取得
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

    return count


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
