"""国会議員白書 (kokkai.sugawarataku.net) スクレイパー

議員の会期別活動統計（発言回数、委員会出席等）を取得する。
個人運営サイトのため、リクエスト間隔を十分に取る。
"""

import logging
import re
import time

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.member import Member

logger = logging.getLogger(__name__)

BASE_URL = "https://kokkai.sugawarataku.net/giin"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GiinScoreBot/1.0; +https://github.com/YotaSakurai/giin-score)",
}
REQUEST_INTERVAL = 2.0  # 個人サイトへの配慮


def _parse_int(text: str) -> int:
    """数値文字列をintに変換する。"""
    text = re.sub(r"[,，\s]", "", text)
    try:
        return int(text)
    except ValueError:
        return 0


def _get_member_ids_from_list(client: httpx.Client, list_url: str) -> list[tuple[str, str]]:
    """議員一覧ページからIDと名前のリストを取得する。

    Returns: [(hakusho_id, name), ...]
    """
    try:
        resp = client.get(list_url)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch {list_url}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    members = []

    for a in soup.find_all("a"):
        href = a.get("href", "")
        # r01920.html or c00563.html
        match = re.search(r"([rc]\d{5})\.html", href)
        if match:
            hakusho_id = match.group(1)
            name = a.get_text(strip=True)
            if name:
                members.append((hakusho_id, name))

    return members


def _scrape_member_stats(client: httpx.Client, hakusho_id: str, target_session: int) -> dict | None:
    """議員個別ページから指定会期の統計データを取得する。

    Returns:
        {
            "speech_count": int,
            "speech_chars": int,
            "written_questions": int,
            "bills_submitted": int,
            "committee_attendance": int,
        }
        or None if not found
    """
    url = f"{BASE_URL}/{hakusho_id}.html"
    try:
        resp = client.get(url)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # テーブルから統計を探す
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            cell_texts = [c.get_text(strip=True) for c in cells]

            # 会期番号が含まれている行を探す
            if not cell_texts:
                continue

            # 「50期」「26期」のような会期/期を探す
            # または会期番号(221等)を直接探す
            for i, text in enumerate(cell_texts):
                if str(target_session) in text or f"{target_session}期" in text:
                    # この行または近くの行にデータがある可能性
                    pass

    # 統計テーブルの構造はページごとに異なるため、
    # より確実なサブページ（hhr/hhc）から取得する方が安全
    return None


def scrape_hakusho_stats(db: Session, session_number: int) -> int:
    """国会議員白書から議員統計を取得する。

    取得したデータはMemberのexternal_idsに保存する。
    """
    client = httpx.Client(headers=HEADERS, timeout=30.0, follow_redirects=True)
    updated = 0

    try:
        # 衆議院の現職一覧（最新会期）
        # 衆議院は「期」で管理されるため、会期番号→期への変換が必要
        # 50期 = 第214回国会以降の衆議院
        # ここでは最新の一覧ページを使う
        shugiin_list_url = f"{BASE_URL}/rl050.html"
        sangiin_list_url = f"{BASE_URL}/cl026.html"

        for list_url, chamber in [
            (shugiin_list_url, "representatives"),
            (sangiin_list_url, "councillors"),
        ]:
            members_list = _get_member_ids_from_list(client, list_url)
            logger.info(f"Hakusho: found {len(members_list)} {chamber} members")

            for hakusho_id, name in members_list:
                # 名前の正規化
                name_normalized = re.sub(r"\s+", "　", name).strip()

                member = (
                    db.query(Member)
                    .filter(Member.name == name_normalized, Member.chamber == chamber)
                    .first()
                )
                if not member:
                    # スペースなしで検索
                    name_no_space = name_normalized.replace("　", "")
                    all_members = db.query(Member).filter(Member.chamber == chamber).all()
                    member = next(
                        (m for m in all_members if m.name.replace("　", "") == name_no_space),
                        None,
                    )

                if not member:
                    continue

                # external_ids に hakusho_id を保存
                if member.external_ids is None:
                    member.external_ids = {}
                if member.external_ids.get("hakusho_id") != hakusho_id:
                    member.external_ids = {**member.external_ids, "hakusho_id": hakusho_id}
                    updated += 1

                time.sleep(REQUEST_INTERVAL)

            db.commit()

    finally:
        client.close()

    logger.info(f"Hakusho: linked {updated} members with hakusho IDs")
    return updated
