"""質問主意書スクレイピング

衆議院・参議院Webサイトから質問主意書一覧を取得する。
"""

import logging
import re
import time
from datetime import UTC, datetime
from datetime import date as date_type
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.models.pipeline import PipelineRun
from app.models.session import DietSession
from app.models.written_question import WrittenQuestion
from app.pipeline.member_master import find_or_create_member, normalize_name
from app.pipeline.utils import USER_AGENT, detect_encoding

logger = logging.getLogger(__name__)

SHUGIIN_BASE = "https://www.shugiin.go.jp"
SANGIIN_BASE = "https://www.sangiin.go.jp"


def scrape_written_questions(db: Session, session_number: int) -> int:
    """衆参両院の質問主意書を取得する。"""
    pipeline_run = PipelineRun(
        pipeline_name="written_questions",
        session_number=session_number,
        status="running",
        started_at=datetime.now(UTC),
    )
    db.add(pipeline_run)
    db.commit()

    total = 0
    try:
        diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
        if not diet_session:
            diet_session = DietSession(session_number=session_number, kind="通常")
            db.add(diet_session)
            db.flush()

        total += _scrape_shugiin(db, diet_session, session_number)
        total += _scrape_sangiin(db, diet_session, session_number)

        db.commit()
        pipeline_run.status = "completed"
        pipeline_run.records_processed = total
        pipeline_run.finished_at = datetime.now(UTC)
        db.commit()
        logger.info(f"Written questions completed: {total} records for session {session_number}")

    except Exception as e:
        pipeline_run.status = "failed"
        pipeline_run.error_message = str(e)
        pipeline_run.finished_at = datetime.now(UTC)
        db.commit()
        logger.error(f"Written questions scraper failed: {e}")
        raise

    return total


def _scrape_shugiin(db: Session, diet_session: DietSession, session_number: int) -> int:
    """衆議院の質問主意書一覧を取得する。"""
    list_url = (
        f"{SHUGIIN_BASE}/internet/itdb_shitsumon.nsf/html/shitsumon/kaiji{session_number}_l.htm"
    )
    count = 0

    with httpx.Client(
        timeout=30.0,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        time.sleep(settings.kokkai_api_rate_limit)
        try:
            resp = client.get(list_url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Shugiin shitsumon page not found for session {session_number}: {e}")
            return 0

        resp.encoding = detect_encoding(resp)
        soup = BeautifulSoup(resp.text, "lxml")

        table = soup.find("table")
        if not table:
            logger.warning(f"No table found on shugiin shitsumon page (session {session_number})")
            return 0

        rows = table.find_all("tr")  # type: ignore[union-attr]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            try:
                q_num = int(cells[0].get_text(strip=True))
            except (ValueError, TypeError):
                continue

            title = cells[1].get_text(strip=True)
            submitter = _clean_shugiin_name(cells[2].get_text(strip=True))
            submitted_str = cells[3].get_text(strip=True)

            if not title or not submitter:
                continue

            # 答弁リンクの有無
            has_answer = False
            answer_url = None
            for a_tag in row.find_all("a", href=True):
                href = a_tag["href"]
                if href.startswith("b") or "/pdfT/" in href:
                    has_answer = True
                    answer_url = urljoin(list_url, href)
                    break

            # 質問リンク
            question_url = None
            for a_tag in row.find_all("a", href=True):
                href = a_tag["href"]
                if href.startswith("a") or href.startswith(str(session_number)) or "/pdfS/" in href:
                    question_url = urljoin(list_url, href)
                    break

            submitted_date = _parse_date(submitted_str)

            # 提出者の議員紐づけ
            member = find_or_create_member(
                db,
                name=normalize_name(submitter),
                chamber="representatives",
            )

            # 重複チェック
            existing = (
                db.query(WrittenQuestion)
                .filter_by(
                    session_id=diet_session.id,
                    chamber="representatives",
                    question_number=q_num,
                )
                .first()
            )
            if existing:
                if has_answer and not existing.has_answer:
                    existing.has_answer = True
                    existing.answer_url = answer_url
                continue

            wq = WrittenQuestion(
                session_id=diet_session.id,
                member_id=member.id,
                chamber="representatives",
                question_number=q_num,
                title=title,
                submitted_date=submitted_date,
                question_url=question_url,
                answer_url=answer_url,
                has_answer=has_answer,
            )
            db.add(wq)
            count += 1

            if count % 100 == 0:
                db.commit()

    db.commit()
    logger.info(f"Shugiin written questions: {count} new records (session {session_number})")
    return count


def _scrape_sangiin(db: Session, diet_session: DietSession, session_number: int) -> int:
    """参議院の質問主意書一覧を取得する。

    参議院のHTML構造（class=list_c テーブル）:
      行1: [th:提出番号] [th:件名] [td:件名テキスト(リンク付き)]
      行2: [td:番号] [td:提出者] [td:氏名] [td:質問HTML] [td:答弁HTML]
      行3: [td:質問PDF] [td:答弁PDF]
    """
    list_url = f"{SANGIIN_BASE}/japanese/joho1/kousei/syuisyo/{session_number}/syuisyo.htm"
    count = 0

    with httpx.Client(
        timeout=30.0,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        time.sleep(settings.kokkai_api_rate_limit)
        try:
            resp = client.get(list_url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Sangiin shitsumon page not found for session {session_number}: {e}")
            return 0

        resp.encoding = detect_encoding(resp)
        soup = BeautifulSoup(resp.text, "lxml")

        table = soup.find("table", class_="list_c")
        if not table:
            logger.warning(f"No list_c table on sangiin shitsumon page (session {session_number})")
            return 0

        rows = table.find_all("tr")  # type: ignore[union-attr]

        # 件名行 → データ行 → PDF行 の3行1組
        # 件名行: [th:提出番号] [th:件名] [td:件名テキスト]
        # データ行: [td:番号] [td:提出者] [td:氏名] [td:質問HTML] ...
        pending_title = ""

        for row in rows:
            cells = row.find_all(["td", "th"])
            cell_texts = [c.get_text(strip=True) for c in cells]

            # 件名行: 「提出番号」「件名」を含むヘッダー行
            if len(cells) >= 3 and "提出番号" in cell_texts[0] and "件名" in cell_texts[1]:
                pending_title = cell_texts[2]
                continue

            # データ行: 先頭が数字、2番目が「提出者」
            if len(cells) >= 3 and "提出者" in cell_texts[1]:
                try:
                    q_num = int(cell_texts[0])
                except (ValueError, TypeError):
                    continue

                submitter = _clean_sangiin_name(cell_texts[2])
                title = pending_title or ""

                # リンク収集
                question_url = None
                answer_url = None
                has_answer = False
                for a_tag in row.find_all("a", href=True):
                    href = a_tag["href"]
                    text = a_tag.get_text(strip=True)
                    if "質問本文" in text and not question_url:
                        question_url = urljoin(list_url, href)
                    if "答弁本文" in text and not answer_url:
                        answer_url = urljoin(list_url, href)
                        has_answer = True

                if not title:
                    continue

                member = None
                if submitter:
                    member = find_or_create_member(
                        db,
                        name=normalize_name(submitter),
                        chamber="councillors",
                    )

                existing = (
                    db.query(WrittenQuestion)
                    .filter_by(
                        session_id=diet_session.id,
                        chamber="councillors",
                        question_number=q_num,
                    )
                    .first()
                )
                if existing:
                    if has_answer and not existing.has_answer:
                        existing.has_answer = True
                        existing.answer_url = answer_url
                else:
                    wq = WrittenQuestion(
                        session_id=diet_session.id,
                        member_id=(member.id if member else None),
                        chamber="councillors",
                        question_number=q_num,
                        title=title,
                        question_url=question_url,
                        answer_url=answer_url,
                        has_answer=has_answer,
                    )
                    db.add(wq)
                    count += 1

                    if count % 100 == 0:
                        db.commit()

                pending_title = ""

    db.commit()
    logger.info(f"Sangiin written questions: {count} new records (session {session_number})")
    return count


def _clean_shugiin_name(text: str) -> str:
    """衆議院の提出者名から敬称を除去。"""
    text = re.sub(r"君$", "", text).strip()
    return text


def _clean_sangiin_name(text: str) -> str:
    """参議院の提出者名から敬称を除去。"""
    text = re.sub(r"君$", "", text).strip()
    text = re.sub(r"さん$", "", text).strip()
    text = re.sub(r"^提出者\s*", "", text)
    return text.strip()


def _parse_date(text: str) -> date_type | None:
    """日付文字列をパースする。令和/平成対応。"""
    if not text:
        return None

    # 令和X年M月D日
    m = re.search(r"令和(\d+)年(\d+)月(\d+)日", text)
    if m:
        year = 2018 + int(m.group(1))
        return date_type(year, int(m.group(2)), int(m.group(3)))

    # 平成X年M月D日
    m = re.search(r"平成(\d+)年(\d+)月(\d+)日", text)
    if m:
        year = 1988 + int(m.group(1))
        return date_type(year, int(m.group(2)), int(m.group(3)))

    # YYYY/MM/DD or YYYY-MM-DD
    m = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text)
    if m:
        return date_type(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    return None
