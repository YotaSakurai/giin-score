"""政治資金収支報告書データローダー

CSVファイルから政治資金データを読み込む。
データソース: political-finance-database.com からダウンロードしたCSV

CSVフォーマット（想定）:
  議員名, 政治団体名, 報告年度, 収入合計, 個人献金, 法人献金,
  政治団体献金, 政党交付金, 党費, パーティー収入, その他収入,
  支出合計, 人件費, 事務所費, 政治活動費, 調査研究費, 組織活動費, その他支出

使用法:
  python -m app.pipeline.political_fund_loader --csv data/political_funds.csv
  python -m app.pipeline.runner --pipeline political_funds
"""

import csv
import logging
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.political_fund import PoliticalFund

logger = logging.getLogger(__name__)

# CSVカラム名の候補マッピング（柔軟に対応）
COLUMN_MAP = {
    # 議員名
    "議員名": "member_name",
    "氏名": "member_name",
    "politician_name": "member_name",
    # 団体名
    "政治団体名": "organization_name",
    "団体名": "organization_name",
    "organization_name": "organization_name",
    # 報告年度
    "報告年度": "report_year",
    "年度": "report_year",
    "year": "report_year",
    # 収入
    "収入合計": "total_income",
    "総収入": "total_income",
    "個人献金": "individual_donations",
    "個人の寄附": "individual_donations",
    "法人献金": "corporate_donations",
    "法人その他の団体からの寄附": "corporate_donations",
    "政治団体献金": "party_donations",
    "政治団体からの寄附": "party_donations",
    "政党交付金": "party_subsidy",
    "本部又は支部から供与された交付金": "party_subsidy",
    "党費": "party_fee",
    "党費又は会費": "party_fee",
    "パーティー収入": "fundraising_party",
    "政治資金パーティー": "fundraising_party",
    "その他収入": "other_income",
    # 支出
    "支出合計": "total_expenditure",
    "総支出": "total_expenditure",
    "人件費": "personnel_expenses",
    "事務所費": "office_expenses",
    "政治活動費": "political_activity",
    "調査研究費": "research_expenses",
    "組織活動費": "organization_expenses",
    "その他支出": "other_expenses",
    "その他の経費": "other_expenses",
}


def _parse_amount(value: str) -> float:
    """金額文字列をfloatに変換する。"""
    if not value:
        return 0.0
    value = re.sub(r"[,，\s円]", "", str(value))
    try:
        return float(value)
    except ValueError:
        return 0.0


def _find_member(db: Session, name: str) -> Member | None:
    """名前で議員を検索する。"""
    # 完全一致
    member = db.query(Member).filter(Member.name == name).first()
    if member:
        return member

    # 全角スペースなしで検索
    name_no_space = name.replace("　", "").replace(" ", "")
    for m in db.query(Member).all():
        if m.name.replace("　", "") == name_no_space:
            return m
    return None


def _detect_columns(header: list[str]) -> dict[str, int]:
    """CSVヘッダーからカラムマッピングを検出する。"""
    mapping = {}
    for i, col in enumerate(header):
        col_clean = col.strip()
        if col_clean in COLUMN_MAP:
            field = COLUMN_MAP[col_clean]
            if field not in mapping:
                mapping[field] = i
    return mapping


def load_political_funds_csv(db: Session, csv_path: str) -> int:
    """CSVファイルから政治資金データを読み込む。"""
    path = Path(csv_path)
    if not path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return 0

    # エンコーディング検出
    encodings = ["utf-8", "utf-8-sig", "shift_jis", "cp932"]
    content = None
    for enc in encodings:
        try:
            content = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue

    if content is None:
        logger.error(f"Cannot decode CSV file: {csv_path}")
        return 0

    reader = csv.reader(content.splitlines())
    header = next(reader, None)
    if not header:
        logger.error("Empty CSV file")
        return 0

    col_map = _detect_columns(header)
    logger.info(f"Detected columns: {col_map}")

    if "member_name" not in col_map:
        logger.error("No member name column found in CSV")
        return 0

    processed = 0
    skipped = 0

    for row in reader:
        if len(row) < 3:
            continue

        name = row[col_map["member_name"]].strip()
        if not name:
            continue

        member = _find_member(db, name)
        if not member:
            skipped += 1
            continue

        org_name = row[col_map.get("organization_name", -1)].strip() if "organization_name" in col_map else f"{name}関連政治団体"
        year = int(row[col_map["report_year"]]) if "report_year" in col_map else 2024

        # upsert
        existing = (
            db.query(PoliticalFund)
            .filter_by(member_id=member.id, report_year=year, organization_name=org_name)
            .first()
        )

        fund_data = {
            "total_income": _parse_amount(row[col_map["total_income"]]) if "total_income" in col_map else 0.0,
            "individual_donations": _parse_amount(row[col_map["individual_donations"]]) if "individual_donations" in col_map else 0.0,
            "corporate_donations": _parse_amount(row[col_map["corporate_donations"]]) if "corporate_donations" in col_map else 0.0,
            "party_donations": _parse_amount(row[col_map["party_donations"]]) if "party_donations" in col_map else 0.0,
            "party_subsidy": _parse_amount(row[col_map["party_subsidy"]]) if "party_subsidy" in col_map else 0.0,
            "party_fee": _parse_amount(row[col_map["party_fee"]]) if "party_fee" in col_map else 0.0,
            "fundraising_party": _parse_amount(row[col_map["fundraising_party"]]) if "fundraising_party" in col_map else 0.0,
            "other_income": _parse_amount(row[col_map["other_income"]]) if "other_income" in col_map else 0.0,
            "total_expenditure": _parse_amount(row[col_map["total_expenditure"]]) if "total_expenditure" in col_map else 0.0,
            "personnel_expenses": _parse_amount(row[col_map["personnel_expenses"]]) if "personnel_expenses" in col_map else 0.0,
            "office_expenses": _parse_amount(row[col_map["office_expenses"]]) if "office_expenses" in col_map else 0.0,
            "political_activity": _parse_amount(row[col_map["political_activity"]]) if "political_activity" in col_map else 0.0,
            "research_expenses": _parse_amount(row[col_map["research_expenses"]]) if "research_expenses" in col_map else 0.0,
            "organization_expenses": _parse_amount(row[col_map["organization_expenses"]]) if "organization_expenses" in col_map else 0.0,
            "other_expenses": _parse_amount(row[col_map["other_expenses"]]) if "other_expenses" in col_map else 0.0,
            "source": str(csv_path),
        }

        if existing:
            for key, val in fund_data.items():
                setattr(existing, key, val)
        else:
            fund = PoliticalFund(
                member_id=member.id,
                report_year=year,
                organization_name=org_name,
                **fund_data,
            )
            db.add(fund)
        processed += 1

        if processed % 100 == 0:
            db.commit()

    db.commit()
    logger.info(f"Political funds loaded: {processed} records, {skipped} skipped (member not found)")
    return processed


def load_political_funds(db: Session, session_number: int) -> int:
    """data/political_funds/ ディレクトリ内のCSVを読み込む。"""
    data_dir = Path("/data/political_funds")
    if not data_dir.exists():
        data_dir = Path("data/political_funds")
    if not data_dir.exists():
        logger.info("No political_funds data directory found, skipping")
        return 0

    total = 0
    for csv_file in sorted(data_dir.glob("*.csv")):
        logger.info(f"Loading {csv_file}")
        total += load_political_funds_csv(db, str(csv_file))

    return total
