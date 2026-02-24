"""議員マスタ構築・名寄せ

国会会議録APIの発言者情報から議員マスタを構築する。
名前のゆれ（全角スペース、旧字体等）を吸収する。
"""

import logging
import re
import unicodedata

from sqlalchemy.orm import Session

from app.models.member import Member

logger = logging.getLogger(__name__)

# 旧字体→新字体マッピング（よく出るもの）
OLD_NEW_KANJI = {
    "齋": "斎",
    "齊": "斎",
    "邊": "辺",
    "邉": "辺",
    "廣": "広",
    "國": "国",
    "島": "島",
    "﨑": "崎",
    "髙": "高",
    "濱": "浜",
    "澤": "沢",
    "櫻": "桜",
    "壽": "寿",
    "實": "実",
    "淵": "渕",
    "藪": "薮",
    "關": "関",
    "鷗": "鴎",
    "龍": "竜",
    "與": "与",
}

# 主要な会派→政党マッピング
FACTION_PARTY_MAP = {
    "自由民主党": "自由民主党",
    "自民": "自由民主党",
    "立憲民主党": "立憲民主党",
    "立憲": "立憲民主党",
    "公明党": "公明党",
    "公明": "公明党",
    "日本維新の会": "日本維新の会",
    "維新": "日本維新の会",
    "国民民主党": "国民民主党",
    "国民": "国民民主党",
    "日本共産党": "日本共産党",
    "共産": "日本共産党",
    "れいわ新選組": "れいわ新選組",
    "れいわ": "れいわ新選組",
    "社会民主党": "社会民主党",
    "社民": "社会民主党",
    "NHK党": "NHK党",
    "参政党": "参政党",
    "無所属": "無所属",
}

# 役職→role_categoryマッピングキーワード
CABINET_KEYWORDS = ["内閣総理大臣", "大臣", "官房長官", "官房副長官"]
CHAIR_KEYWORDS = ["委員長", "議長", "副議長"]
OPPOSITION_SENIOR_KEYWORDS = ["幹事長", "政調会長", "国対委員長", "代表"]


def normalize_name(name: str) -> str:
    """氏名を正規化する。"""
    # NFKC正規化（全角→半角数字等）
    name = unicodedata.normalize("NFKC", name)
    # 旧字体→新字体
    for old, new in OLD_NEW_KANJI.items():
        name = name.replace(old, new)
    # スペースの正規化（全角スペース→半角、連続スペース→単一）
    name = name.replace("\u3000", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name


def guess_party(faction: str) -> str | None:
    """会派名から政党名を推定する。"""
    if not faction:
        return None
    for keyword, party in FACTION_PARTY_MAP.items():
        if keyword in faction:
            return party
    return faction


def guess_role_category(role: str, party: str | None) -> str:
    """役職情報からrole_categoryを推定する。"""
    if not role:
        ruling = _is_ruling_party(party)
        return "ruling_junior" if ruling else "opposition_junior"

    for kw in CABINET_KEYWORDS:
        if kw in role:
            return "cabinet"
    for kw in CHAIR_KEYWORDS:
        if kw in role:
            return "chair"

    ruling = _is_ruling_party(party)
    if ruling:
        return "ruling_junior"

    for kw in OPPOSITION_SENIOR_KEYWORDS:
        if kw in role:
            return "opposition_senior"

    return "opposition_junior"


def _is_ruling_party(party: str | None) -> bool:
    if not party:
        return False
    return party in ("自由民主党", "公明党")


def find_or_create_member(
    db: Session,
    name: str,
    chamber: str,
    party: str | None = None,
    role: str | None = None,
) -> Member:
    """議員を検索し、なければ新規作成する。"""
    normalized = normalize_name(name)
    member = db.query(Member).filter_by(name=normalized, chamber=chamber).first()

    if member:
        # 既存メンバーの情報を更新（新しい情報があれば）
        if party and not member.party:
            member.party = guess_party(party)
        if role:
            member.role_category = guess_role_category(role, member.party)
        return member

    guessed_party = guess_party(party)
    new_member = Member(
        name=normalized,
        chamber=chamber,
        party=guessed_party,
        faction=party,
        role_category=guess_role_category(role, guessed_party),
    )
    db.add(new_member)
    db.flush()
    logger.info(f"Created member: {normalized} ({chamber}, {guessed_party})")
    return new_member
