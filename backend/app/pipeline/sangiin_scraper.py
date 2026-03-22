"""参議院投票データスクレイピング

参議院Webサイトの投票結果ページから個別議員の投票記録を取得する。
Session 213以降の新HTML構造（div/dl/flex）と旧構造（table）の両方に対応。
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
    base_dir = base_url.rsplit("/", 1)[0]
    links = []
    seen = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # 個別投票結果ページ（例: 213-0619-v001.htm）のパターン
        if href.endswith(".htm") and "-v" in href:
            if href.startswith("http"):
                full_url = href
            elif href.startswith("/"):
                full_url = f"{BASE_URL}{href}"
            else:
                full_url = f"{base_dir}/{href}"
            if full_url not in seen:
                seen.add(full_url)
                links.append(full_url)
    return links


def _scrape_vote_page(db: Session, client: httpx.Client, session_number: int, url: str) -> int:
    """個別の投票結果ページをスクレイピングする。"""
    resp = client.get(url)
    resp.raise_for_status()
    resp.encoding = detect_encoding(resp)

    soup = BeautifulSoup(resp.text, "lxml")
    contents = soup.find(id="ContentsBox")

    # HTML構造の判定: 新構造は <h1> を持つ、旧構造は <table> から始まる
    is_new_layout = bool(contents and contents.find("h1"))

    if is_new_layout:
        return _scrape_vote_page_new(db, soup, contents, session_number)
    else:
        return _scrape_vote_page_legacy(db, soup, session_number)


def _scrape_vote_page_new(db: Session, soup: BeautifulSoup, contents, session_number: int) -> int:
    """新構造（Session 213以降）の投票ページをパースする。"""
    # 議案名を取得（dl.ankenmei > dd）
    bill_title = _extract_title_new(contents)
    if not bill_title:
        return 0

    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        return 0

    bill = _find_or_create_bill(db, diet_session.id, bill_title)

    # 起立採決チェック
    kiritsu = contents.find("p", class_="kiritsu")
    if kiritsu:
        result_text = "可決" if "可決" in kiritsu.get_text() else "否決"
        existing = db.query(VoteResult).filter_by(bill_id=bill.id, chamber="councillors").first()
        if not existing:
            vote_result = VoteResult(
                bill_id=bill.id,
                chamber="councillors",
                ayes=0,
                nays=0,
                result=result_text,
            )
            db.add(vote_result)
        return 0

    # 記名投票: h3.tohyosousu から集計結果を取得
    ayes, nays = _extract_totals_new(contents)

    body_text = soup.get_text()
    result_text = None
    if "可決" in body_text:
        result_text = "可決"
    elif "否決" in body_text:
        result_text = "否決"

    existing = db.query(VoteResult).filter_by(bill_id=bill.id, chamber="councillors").first()
    if existing:
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

    # 個別議員の投票記録（dl.sanpilist から）
    count = 0
    for dl in contents.find_all("dl", class_="sanpilist"):
        # dlの直前のh4.partyから党派名を取得（ログ用）
        party_elem = dl.find_previous_sibling("h4", class_="party")
        party_name = party_elem.get_text(strip=True) if party_elem else "unknown"

        text = dl.get_text()
        # テキストから「賛成XXX」「反対XXX」「投票なしXXX」を抽出
        records = _parse_sanpilist_text(text)
        for name, vote_value in records:
            member = find_or_create_member(
                db,
                name=normalize_name(name),
                chamber="councillors",
                party=_clean_party_name(party_name),
            )
            existing_record = (
                db.query(VoteRecord)
                .filter_by(vote_result_id=vote_result.id, member_id=member.id)
                .first()
            )
            if not existing_record:
                record = VoteRecord(
                    vote_result_id=vote_result.id,
                    member_id=member.id,
                    vote=vote_value,
                )
                db.add(record)
                count += 1

    return count


def _extract_title_new(contents) -> str:
    """新構造から議案名を抽出する。"""
    ankenmei = contents.find("dl", class_="ankenmei")
    if ankenmei:
        dd = ankenmei.find("dd")
        if dd:
            title = dd.get_text(strip=True)
            title = re.sub(r"^日程第\S+\s*", "", title)
            title = re.sub(r"（[^）]*提出[^）]*）$", "", title)
            return title.strip()
    return ""


def _extract_totals_new(contents) -> tuple[int, int]:
    """新構造から投票総数の賛成/反対を抽出する。"""
    ayes, nays = 0, 0
    tohyo = contents.find("h3", class_="tohyosousu")
    if tohyo:
        text = tohyo.get_text()
        m_ayes = re.search(r"賛成票\s*(\d+)", text)
        m_nays = re.search(r"反対票\s*(\d+)", text)
        if m_ayes:
            ayes = int(m_ayes.group(1))
        if m_nays:
            nays = int(m_nays.group(1))
    return ayes, nays


def _parse_sanpilist_text(text: str) -> list[tuple[str, str]]:
    """sanpilistテキストから(氏名, vote_value)のリストを抽出する。

    テキスト例: "賛成票 112　　　反対票   0賛成足立　　敏之賛成阿達 　 雅志..."
    """
    records = []
    # 「賛成票 N　反対票 N」ヘッダー行を除去
    text = re.sub(r"賛成票\s*\d+\s*反対票\s*\d+", "", text)

    # パターン: (賛成|反対|投票なし)(氏名) の繰り返し
    # 氏名は漢字/ひらがな/カタカナ/全角スペースで構成
    name_chars = r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\u3000\s]"
    lookahead = r"(?=賛成|反対|投票なし|$)"
    pattern = rf"(賛成|反対|投票なし)({name_chars}{{2,}}?){lookahead}"
    for m in re.finditer(pattern, text):
        vote_text = m.group(1)
        name = m.group(2).strip()
        name = re.sub(r"[\s\u3000]+", "\u3000", name)  # スペースを全角1つに統一

        if not name or len(name) < 2:
            continue

        if vote_text == "賛成":
            records.append((name, "aye"))
        elif vote_text == "反対":
            records.append((name, "nay"))
        elif vote_text == "投票なし":
            records.append((name, "abstain"))

    return records


def _clean_party_name(text: str) -> str:
    """政党名から人数表記を除去する。"""
    return re.sub(r"\(\s*\d+名?\s*\)", "", text).strip()


def _scrape_vote_page_legacy(db: Session, soup: BeautifulSoup, session_number: int) -> int:
    """旧構造（Session 212以前）の投票ページをパースする。"""
    body_text = soup.get_text()

    # 議案名を取得
    bill_title = ""
    for dt in soup.find_all("dt"):
        if "案件名" in dt.get_text():
            dd = dt.find_next_sibling("dd")
            if dd:
                bill_title = dd.get_text(strip=True)
                bill_title = re.sub(r"^日程第\d+\s*", "", bill_title)
                bill_title = re.sub(r"（[^）]*提出[^）]*）$", "", bill_title)
                bill_title = bill_title.strip()
            break

    if not bill_title:
        # 旧構造フォールバック: tableセル内の案件名
        for table in soup.find_all("table"):
            for cell in table.find_all(["td", "th"]):
                if "案件名" in cell.get_text():
                    next_cell = cell.find_next_sibling("td")
                    if next_cell:
                        bill_title = next_cell.get_text(strip=True)
                        bill_title = re.sub(r"^日程第\d+\s*", "", bill_title)
                        bill_title = re.sub(r"（[^）]*提出[^）]*）$", "", bill_title)
                        bill_title = bill_title.strip()
                    break

    if not bill_title:
        return 0

    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        return 0

    bill = _find_or_create_bill(db, diet_session.id, bill_title)

    result_text = None
    if "可決" in body_text:
        result_text = "可決"
    elif "否決" in body_text:
        result_text = "否決"

    # 起立採決チェック
    if "起立採決" in body_text:
        existing = db.query(VoteResult).filter_by(bill_id=bill.id, chamber="councillors").first()
        if not existing:
            vote_result = VoteResult(
                bill_id=bill.id,
                chamber="councillors",
                ayes=0,
                nays=0,
                result=result_text,
            )
            db.add(vote_result)
        return 0

    existing = db.query(VoteResult).filter_by(bill_id=bill.id, chamber="councillors").first()
    if existing:
        return 0

    # 旧構造: table から集計と個別投票を抽出
    ayes, nays = 0, 0
    tables = soup.find_all("table")

    # 集計結果（賛成/反対のヘッダー行を持つ table）
    vote_tables = []
    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue
        first_row_text = rows[0].get_text(strip=True)
        if "賛成" in first_row_text and "反対" in first_row_text:
            vote_tables.append(table)

    vote_result = VoteResult(
        bill_id=bill.id,
        chamber="councillors",
        ayes=ayes,
        nays=nays,
        result=result_text,
    )
    db.add(vote_result)
    db.flush()

    # 個別投票記録（旧table構造: 3列組×3で氏名+賛成/反対マーク）
    count = 0
    for table in vote_tables:
        rows = table.find_all("tr")
        for row in rows[1:]:  # ヘッダー行をスキップ
            cells = row.find_all("td")
            # 3列ごとに(賛成, 反対, 氏名)の組
            for group_start in range(0, len(cells) - 2, 3):
                pro_cell = cells[group_start]
                con_cell = cells[group_start + 1]
                name_cell = cells[group_start + 2]

                name = name_cell.get_text(strip=True)
                if not name or len(name) < 2:
                    continue

                # 賛成/反対は画像またはテキストで判定
                pro_img = pro_cell.find("img")
                con_img = con_cell.find("img")
                pro_text = pro_cell.get_text(strip=True)
                con_text = con_cell.get_text(strip=True)

                vote_value = None
                if pro_img or pro_text in ("○", "〇", "賛成"):
                    vote_value = "aye"
                    ayes += 1
                elif con_img or con_text in ("×", "✕", "反対"):
                    vote_value = "nay"
                    nays += 1

                if not vote_value:
                    continue

                member = find_or_create_member(
                    db,
                    name=normalize_name(name),
                    chamber="councillors",
                )

                existing_record = (
                    db.query(VoteRecord)
                    .filter_by(vote_result_id=vote_result.id, member_id=member.id)
                    .first()
                )
                if not existing_record:
                    record = VoteRecord(
                        vote_result_id=vote_result.id,
                        member_id=member.id,
                        vote=vote_value,
                    )
                    db.add(record)
                    count += 1

    # 集計値を更新
    vote_result.ayes = ayes
    vote_result.nays = nays

    return count


def _find_or_create_bill(db, session_id: int, bill_title: str):
    """タイトルの先頭30文字で部分一致検索し、なければ作成する。"""
    search_title = bill_title[:30] if len(bill_title) > 30 else bill_title
    bill = (
        db.query(Bill)
        .filter(
            Bill.session_id == session_id,
            Bill.title.contains(search_title),
        )
        .first()
    )
    if not bill:
        bill = Bill(
            session_id=session_id,
            bill_kind="その他",
            title=bill_title,
        )
        db.add(bill)
        db.flush()
        logger.info(f"Auto-created bill: {bill_title[:50]}")
    return bill


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
