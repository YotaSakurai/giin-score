"""衆議院・参議院の委員会名簿スクレイパー

衆議院: Shift_JIS、テーブル形式（役職/氏名/ふりがな/会派）
参議院: UTF-8、テーブル形式（役職/氏名/会派名）
"""

import logging
import re
import time

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.committee import CommitteeMembership
from app.models.member import Member
from app.models.session import DietSession

logger = logging.getLogger(__name__)

SHUGIIN_BASE = "https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai"
SANGIIN_BASE = "https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list"
SANGIIN_INDEX = "https://www.sangiin.go.jp/japanese/kon_kokkaijyoho/index.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GiinScoreBot/1.0)",
}


def _normalize_name(name: str) -> str:
    """議員名を正規化する。「君」除去、全角スペース統一。"""
    name = name.strip()
    name = re.sub(r"君$", "", name)
    name = re.sub(r"\s+", "　", name)  # 連続スペースを全角1つに
    name = re.sub(r"　+", "　", name)
    return name


def _find_member(db: Session, name: str, chamber: str) -> Member | None:
    """名前と院で議員を検索する。"""
    member = db.query(Member).filter(Member.name == name, Member.chamber == chamber).first()
    if member:
        return member
    # 全角スペースなしでも試行
    name_no_space = name.replace("　", "")
    members = db.query(Member).filter(Member.chamber == chamber).all()
    for m in members:
        if m.name.replace("　", "") == name_no_space:
            return m
    return None


def _classify_committee(name: str) -> str:
    """委員会名から種類を判定する。"""
    if "特別委員会" in name:
        return "特別"
    if "審査会" in name:
        return "審査会"
    if "調査会" in name:
        return "調査会"
    return "常任"


def _scrape_shugiin_committees(db: Session, diet_session: DietSession, client: httpx.Client) -> int:
    """衆議院の委員会名簿をスクレイピングする。"""
    # 委員会一覧ページを取得
    list_url = f"{SHUGIIN_BASE}/list.htm"
    resp = client.get(list_url)
    resp.encoding = "shift_jis"
    soup = BeautifulSoup(resp.text, "html.parser")

    # 委員会リンクを取得
    committee_links = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href.startswith("iin_") and href.endswith(".htm"):
            committee_links.append((a.get_text(strip=True), href))

    logger.info(f"Shugiin: found {len(committee_links)} committees")

    total = 0
    for committee_name_raw, href in committee_links:
        url = f"{SHUGIIN_BASE}/{href}"
        try:
            resp = client.get(url)
            resp.encoding = "shift_jis"
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            continue

        page_soup = BeautifulSoup(resp.text, "html.parser")

        # H4からフル委員会名を取得
        h4 = page_soup.find("h4")
        committee_name = committee_name_raw
        if h4:
            text = h4.get_text(strip=True)
            # 「内閣委員会　委員名簿」 → 「内閣委員会」
            committee_name = re.sub(r"[　\s]+委員名簿.*", "", text)

        committee_type = _classify_committee(committee_name)

        # テーブルから委員を取得
        table = page_soup.find("table", class_="table")
        if not table:
            continue

        rows = table.find_all("tr")
        for row in rows[1:]:  # ヘッダー行をスキップ
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            role = cells[0].get_text(strip=True) or "委員"
            name_raw = cells[1].get_text(strip=True)
            name = _normalize_name(name_raw)

            if not name:
                continue

            member = _find_member(db, name, "representatives")
            if not member:
                continue

            # 重複チェック
            existing = (
                db.query(CommitteeMembership)
                .filter_by(
                    member_id=member.id,
                    session_id=diet_session.id,
                    committee_name=committee_name,
                )
                .first()
            )
            if existing:
                existing.role = role
                existing.committee_type = committee_type
            else:
                cm = CommitteeMembership(
                    member_id=member.id,
                    session_id=diet_session.id,
                    committee_name=committee_name,
                    chamber="representatives",
                    role=role,
                    committee_type=committee_type,
                )
                db.add(cm)
                total += 1

        time.sleep(0.5)

    db.commit()
    logger.info(f"Shugiin: {total} committee memberships added")
    return total


def _scrape_sangiin_committees(db: Session, diet_session: DietSession, client: httpx.Client) -> int:
    """参議院の委員会名簿をスクレイピングする。"""
    # 委員会一覧ページを取得
    resp = client.get(SANGIIN_INDEX)
    soup = BeautifulSoup(resp.text, "html.parser")

    # 委員会リンクを取得
    committee_links = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if "/list/l" in href and href.endswith(".htm"):
            name = a.get_text(strip=True)
            if name:
                # 相対パスを絶対パスに変換
                full_url = f"https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/{href.split('list/')[-1]}"
                committee_links.append((name, full_url))

    logger.info(f"Sangiin: found {len(committee_links)} committees")

    total = 0
    for committee_name_raw, url in committee_links:
        try:
            resp = client.get(url)
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            continue

        page_soup = BeautifulSoup(resp.text, "html.parser")

        # H3からフル委員会名を取得
        h3 = page_soup.find("h3")
        committee_name = committee_name_raw
        if h3:
            text = h3.get_text(strip=True)
            committee_name = re.sub(r"^参議院", "", text).strip()

        committee_type = _classify_committee(committee_name)

        # テーブルから委員を取得
        table = page_soup.find("table", class_="list_c")
        if not table:
            continue

        rows = table.find_all("tr")
        for row in rows[1:]:  # ヘッダー行をスキップ
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            role_text = cells[0].get_text(strip=True)
            role = role_text if role_text else "委員"
            name_raw = cells[1].get_text(strip=True)
            name = _normalize_name(name_raw)

            if not name:
                continue

            member = _find_member(db, name, "councillors")
            if not member:
                continue

            existing = (
                db.query(CommitteeMembership)
                .filter_by(
                    member_id=member.id,
                    session_id=diet_session.id,
                    committee_name=committee_name,
                )
                .first()
            )
            if existing:
                existing.role = role
                existing.committee_type = committee_type
            else:
                cm = CommitteeMembership(
                    member_id=member.id,
                    session_id=diet_session.id,
                    committee_name=committee_name,
                    chamber="councillors",
                    role=role,
                    committee_type=committee_type,
                )
                db.add(cm)
                total += 1

        time.sleep(0.5)

    db.commit()
    logger.info(f"Sangiin: {total} committee memberships added")
    return total


def scrape_committees(db: Session, session_number: int) -> int:
    """衆参両院の委員会名簿をスクレイピングする。"""
    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        diet_session = DietSession(session_number=session_number, kind="通常")
        db.add(diet_session)
        db.flush()

    client = httpx.Client(headers=HEADERS, timeout=30.0, follow_redirects=True)
    total = 0

    try:
        total += _scrape_shugiin_committees(db, diet_session, client)
        total += _scrape_sangiin_committees(db, diet_session, client)
    finally:
        client.close()

    logger.info(f"Committee memberships completed: {total} records for session {session_number}")
    return total
