"""SmartNews SMRI GitHub CSV取り込み

法案データCSVを読み込み、bills/diet_sessionsテーブルに保存する。
"""
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.models.bill import Bill
from app.models.pipeline import PipelineRun
from app.models.session import DietSession

logger = logging.getLogger(__name__)


def load_bills_csv(db: Session, csv_path: str | None = None) -> int:
    """CSVファイルから法案データを読み込む。"""
    if csv_path is None:
        csv_dir = Path(settings.data_dir) / "smartnews_csv"
        csv_files = sorted(csv_dir.glob("*.csv"))
        if not csv_files:
            logger.warning(f"No CSV files found in {csv_dir}")
            return 0
    else:
        csv_files = [Path(csv_path)]

    pipeline_run = PipelineRun(
        pipeline_name="smartnews_bills",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(pipeline_run)
    db.commit()

    total_processed = 0

    try:
        for csv_file in csv_files:
            logger.info(f"Loading: {csv_file}")
            try:
                df = pd.read_csv(csv_file, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(csv_file, encoding="cp932")

            for _, row in df.iterrows():
                try:
                    processed = _process_bill_row(db, row)
                    if processed:
                        total_processed += 1
                except Exception as e:
                    logger.warning(f"Failed to process row: {e}")

                if total_processed % 500 == 0 and total_processed > 0:
                    db.commit()

        db.commit()
        pipeline_run.status = "completed"
        pipeline_run.records_processed = total_processed
        pipeline_run.finished_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Loaded {total_processed} bills from CSV")

    except Exception as e:
        pipeline_run.status = "failed"
        pipeline_run.error_message = str(e)
        pipeline_run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise

    return total_processed


def _process_bill_row(db: Session, row) -> bool:
    """CSVの1行を処理してbillsテーブルに保存する。"""
    # カラム名はSmartNews CSVのフォーマットに合わせる
    session_num = _get_field(row, ["session", "国会回次", "session_number"])
    bill_kind = _get_field(row, ["bill_kind", "議案種類", "kind"])
    bill_number = _get_field(row, ["bill_number", "議案番号", "number"])
    title = _get_field(row, ["title", "議案名", "bill_name"])
    status = _get_field(row, ["status", "状態", "審議状況"])
    result = _get_field(row, ["result", "結果", "議決結果"])
    proposer_type = _get_field(row, ["proposer_type", "提出者種別"])
    url = _get_field(row, ["url", "URL"])

    if not title or not session_num:
        return False

    session_num = int(session_num)

    # 会期を取得または作成
    diet_session = db.query(DietSession).filter_by(session_number=session_num).first()
    if not diet_session:
        diet_session = DietSession(session_number=session_num, kind="通常")
        db.add(diet_session)
        db.flush()

    # 重複チェック
    existing = (
        db.query(Bill)
        .filter_by(session_id=diet_session.id, bill_kind=bill_kind or "", title=title)
        .first()
    )
    if existing:
        return False

    bill = Bill(
        session_id=diet_session.id,
        bill_kind=bill_kind or "",
        bill_number=str(bill_number) if bill_number else None,
        title=title,
        status=status,
        result=result,
        proposer_type=proposer_type,
        url=url,
    )
    db.add(bill)
    return True


def _get_field(row, candidates: list[str]) -> str | None:
    """複数のカラム名候補から値を取得する。"""
    for name in candidates:
        if name in row.index:
            val = row[name]
            if pd.notna(val):
                return str(val).strip()
    return None
