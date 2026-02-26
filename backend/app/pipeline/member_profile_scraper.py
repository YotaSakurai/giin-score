"""議員プロフィール（選挙区・読み仮名）スクレイピング

衆議院・参議院の公式議員一覧ページから選挙区情報を取得し、
既存のmembersテーブルを更新する。
"""

import logging
import re
import time
import unicodedata
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.models.member import Member
from app.models.pipeline import PipelineRun
from app.pipeline.member_master import normalize_name
from app.pipeline.utils import USER_AGENT

logger = logging.getLogger(__name__)

# 衆議院議員一覧の50音別ページ (1=あ行 ~ 10=わ行)
SHUGIIN_BASE = "https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/syu"
SHUGIIN_PAGES = [f"{SHUGIIN_BASE}/{i}giin.htm" for i in range(1, 11)]

# 参議院議員一覧
SANGIIN_URL = "https://www.sangiin.go.jp/japanese/joho1/kousei/giin/current/giin.htm"

# 会派略称→政党名マッピング (公式サイトは略称を使う)
FACTION_SHORT = {
    "自民": "自由民主党",
    "立憲": "立憲民主党",
    "公明": "公明党",
    "維新": "日本維新の会",
    "国民": "国民民主党",
    "共産": "日本共産党",
    "れいわ": "れいわ新選組",
    "社民": "社会民主党",
    "参政": "参政党",
    "中道": "中道",
    "各派": "各派に属しない議員",
    "沖縄": "沖縄社会大衆党",
}

# 衆議院の選挙区から都道府県を抽出するパターン
PREFECTURE_PATTERN = re.compile(
    r"^(北海道|青森|岩手|宮城|秋田|山形|福島|茨城|栃木|群馬|埼玉|千葉|東京"
    r"|神奈川|新潟|富山|石川|福井|山梨|長野|岐阜|静岡|愛知|三重|滋賀|京都"
    r"|大阪|兵庫|奈良|和歌山|鳥取|島根|岡山|広島|山口|徳島|香川|愛媛|高知"
    r"|福岡|佐賀|長崎|熊本|大分|宮崎|鹿児島|沖縄)"
)

# 衆議院比例ブロック
HIREI_BLOCKS = [
    "北海道",
    "東北",
    "北関東",
    "南関東",
    "東京",
    "北陸信越",
    "東海",
    "近畿",
    "中国",
    "四国",
    "九州",
]


def scrape_member_profiles(db: Session) -> int:
    """衆参両院の議員一覧から選挙区情報をスクレイピングして更新する。"""
    pipeline_run = PipelineRun(
        pipeline_name="member_profiles",
        session_number=0,
        status="running",
        started_at=datetime.now(UTC),
    )
    db.add(pipeline_run)
    db.commit()

    total_updated = 0

    try:
        with httpx.Client(
            timeout=30.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        ) as client:
            total_updated += _scrape_shugiin(db, client)
            total_updated += _scrape_sangiin(db, client)

        db.commit()
        pipeline_run.status = "completed"
        pipeline_run.records_processed = total_updated
        pipeline_run.finished_at = datetime.now(UTC)
        db.commit()
        logger.info(f"Member profiles updated: {total_updated} members")

    except Exception as e:
        pipeline_run.status = "failed"
        pipeline_run.error_message = str(e)
        pipeline_run.finished_at = datetime.now(UTC)
        db.commit()
        logger.error(f"Member profile scraper failed: {e}")
        raise

    return total_updated


def _scrape_shugiin(db: Session, client: httpx.Client) -> int:
    """衆議院議員一覧から選挙区情報を取得する。"""
    updated = 0

    for page_url in SHUGIIN_PAGES:
        time.sleep(settings.kokkai_api_rate_limit)
        try:
            resp = client.get(page_url)
            resp.raise_for_status()
            # 衆議院はShift_JISの場合がある
            content_type = resp.headers.get("content-type", "").lower()
            if "shift_jis" in content_type or "sjis" in content_type:
                resp.encoding = "shift_jis"
            else:
                # metaタグからも判定
                raw = resp.content
                if b"Shift_JIS" in raw or b"shift_jis" in raw:
                    resp.encoding = "shift_jis"
                else:
                    resp.encoding = "utf-8"

            soup = BeautifulSoup(resp.text, "lxml")
            rows = soup.find_all("tr", valign="top")

            for tr in rows:
                tds = tr.find_all("td")
                if len(tds) < 5:
                    continue

                # データ行かどうか判定（ヘッダー行はclass="sh1td1"等が固定）
                raw_name = tds[0].get_text(strip=True)
                if raw_name in ("氏名", ""):
                    continue

                # 「君」を除去
                name = raw_name.rstrip("君")
                name = normalize_name(name)

                reading = tds[1].get_text(strip=True)
                reading = unicodedata.normalize("NFKC", reading).replace("\u3000", " ")
                reading = re.sub(r"\s+", " ", reading).strip()

                party_short = tds[2].get_text(strip=True)
                district_text = tds[3].get_text(strip=True)

                # 選挙区の正規化
                district = _normalize_shugiin_district(district_text)

                # 既存メンバーとマッチング
                member = db.query(Member).filter_by(name=name, chamber="representatives").first()
                if member:
                    changed = False
                    if district and member.district != district:
                        member.district = district
                        changed = True
                    if reading and not member.name_reading:
                        member.name_reading = reading
                        changed = True
                    if not member.party and party_short:
                        member.party = FACTION_SHORT.get(party_short, party_short)
                        changed = True
                    if changed:
                        updated += 1

        except Exception as e:
            logger.warning(f"Failed to scrape Shugiin page {page_url}: {e}")

    logger.info(f"Shugiin: updated {updated} members")
    return updated


def _normalize_shugiin_district(text: str) -> str:
    """衆議院の選挙区表記を正規化する。"""
    text = unicodedata.normalize("NFKC", text).strip()
    # 比例代表: "(比)ブロック名" or "（比）ブロック名"
    hirei_match = re.match(r"[（(]比[）)]\s*(.+)", text)
    if hirei_match:
        block = hirei_match.group(1).strip()
        return f"比例{block}"

    # 小選挙区: "県名+数字" -> "県名N区"
    pref_match = PREFECTURE_PATTERN.match(text)
    if pref_match:
        pref = pref_match.group(1)
        rest = text[len(pref) :].strip()
        if rest.isdigit():
            return f"{pref}{rest}区"
        return text

    return text


def _scrape_sangiin(db: Session, client: httpx.Client) -> int:
    """参議院議員一覧から選挙区情報を取得する。"""
    updated = 0

    time.sleep(settings.kokkai_api_rate_limit)
    try:
        resp = client.get(SANGIIN_URL)
        resp.raise_for_status()
        resp.encoding = "utf-8"

        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.find("table", attrs={"summary": re.compile("議員一覧")})
        if not table:
            # fallback: class="list" のテーブルを探す
            table = soup.find("table", class_="list")
        if not table:
            logger.warning("Sangiin member list table not found")
            return 0

        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue

            # 氏名
            name_cell = tds[0]
            raw_name = name_cell.get_text(strip=True)
            if not raw_name:
                continue
            name = normalize_name(raw_name)

            reading = tds[1].get_text(strip=True)
            reading = unicodedata.normalize("NFKC", reading).replace("\u3000", " ")
            reading = re.sub(r"\s+", " ", reading).strip()

            party_short = tds[2].get_text(strip=True)
            district_text = tds[3].get_text(strip=True)

            # 参議院の選挙区: 都道府県名 or "比例"
            district = district_text if district_text else None

            member = db.query(Member).filter_by(name=name, chamber="councillors").first()
            if member:
                changed = False
                if district and member.district != district:
                    member.district = district
                    changed = True
                if reading and not member.name_reading:
                    member.name_reading = reading
                    changed = True
                if not member.party and party_short:
                    member.party = FACTION_SHORT.get(party_short, party_short)
                    changed = True
                if changed:
                    updated += 1

    except Exception as e:
        logger.warning(f"Failed to scrape Sangiin members: {e}")

    logger.info(f"Sangiin: updated {updated} members")
    return updated
