"""デイリー分析パイプライン

パイプライン実行後にデータ品質を分析し、Discord通知で結果を送信する。
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.models.member import Member
from app.models.pipeline import PipelineRun
from app.models.score import MemberScore
from app.models.session import DietSession
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore
from app.models.vote import VoteRecord, VoteResult
from app.models.written_question import WrittenQuestion
from app.pipeline.notify import _send_webhook

logger = logging.getLogger(__name__)


def _grade_distribution(db: Session, session_id: int) -> dict[str, int]:
    """グレード分布を取得する。"""
    rows = db.execute(
        select(MemberScore.grade, func.count(MemberScore.id))
        .where(MemberScore.session_id == session_id)
        .group_by(MemberScore.grade)
    ).all()
    return {row[0]: row[1] for row in rows}


def _coverage_rate(scored: int, total: int) -> str:
    if total == 0:
        return "N/A"
    pct = scored / total * 100
    if pct >= 90:
        return f"✅ {pct:.0f}%"
    elif pct >= 70:
        return f"⚠️ {pct:.0f}%"
    else:
        return f"❌ {pct:.0f}%"


def analyze_data_quality(db: Session, session_number: int) -> int:
    """データ品質を分析しDiscord通知で送信する。"""
    diet_session = db.execute(
        select(DietSession).where(DietSession.session_number == session_number)
    ).scalar_one_or_none()

    if not diet_session:
        logger.warning(f"Session {session_number} not found, skipping analysis")
        return 0

    sid = diet_session.id

    # 基本メトリクス
    total_members = db.execute(select(func.count(Member.id))).scalar_one()
    scored_members = db.execute(
        select(func.count(MemberScore.id)).where(MemberScore.session_id == sid)
    ).scalar_one()
    speech_count = db.execute(
        select(func.count(Speech.id)).where(Speech.session_id == sid)
    ).scalar_one()
    speakers_count = db.execute(
        select(func.count(func.distinct(Speech.member_id))).where(Speech.session_id == sid)
    ).scalar_one()
    bill_count = db.execute(select(func.count(Bill.id)).where(Bill.session_id == sid)).scalar_one()
    vote_result_count = db.execute(
        select(func.count(VoteResult.id)).where(
            VoteResult.bill_id.in_(select(Bill.id).where(Bill.session_id == sid))
        )
    ).scalar_one()
    vote_record_count = db.execute(
        select(func.count(VoteRecord.id)).where(
            VoteRecord.vote_result_id.in_(
                select(VoteResult.id).where(
                    VoteResult.bill_id.in_(select(Bill.id).where(Bill.session_id == sid))
                )
            )
        )
    ).scalar_one()
    wq_count = db.execute(
        select(func.count(WrittenQuestion.id)).where(WrittenQuestion.session_id == sid)
    ).scalar_one()
    quality_count = db.execute(
        select(func.count(SpeechQualityScore.id)).where(SpeechQualityScore.session_id == sid)
    ).scalar_one()

    # グレード分布
    grades = _grade_distribution(db, sid)
    grade_line = " / ".join(f"{g}:{grades.get(g, 0)}" for g in ["A", "B", "C", "D", "F"])

    # 平均スコア
    avg_score = db.execute(
        select(func.avg(MemberScore.total)).where(MemberScore.session_id == sid)
    ).scalar_one()
    avg_score_str = f"{avg_score:.1f}" if avg_score else "N/A"

    # 最終パイプライン実行
    last_runs = (
        db.execute(
            select(PipelineRun)
            .where(PipelineRun.status == "completed")
            .order_by(PipelineRun.finished_at.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )
    last_run_line = ""
    if last_runs:
        latest = last_runs[0]
        ts = latest.finished_at.strftime("%Y-%m-%d %H:%M") if latest.finished_at else "N/A"
        last_run_line = f"\n**最終実行:** {ts}"

    # データギャップ分析
    gaps: list[str] = []
    if scored_members < total_members * 0.5:
        gaps.append(f"スコア計算済み議員が少ない ({scored_members}/{total_members})")
    if speech_count == 0:
        gaps.append("発言データが0件")
    if bill_count == 0:
        gaps.append("法案データが0件")
    if vote_record_count == 0:
        gaps.append("投票記録が0件")
    if quality_count < speakers_count * 0.3 and speakers_count > 0:
        gaps.append(f"質問品質分析のカバー率が低い ({quality_count}/{speakers_count}発言者)")

    gaps_text = "\n".join(f"⚠️ {g}" for g in gaps) if gaps else "✅ データギャップなし"

    # Discord通知
    description = (
        f"**会期:** {session_number}\n"
        f"**議員数:** {total_members}"
        f" (スコア済み: {_coverage_rate(scored_members, total_members)})\n"
        f"**発言:** {speech_count:,}件 ({speakers_count}名)\n"
        f"**法案:** {bill_count:,}件 / 投票結果: {vote_result_count:,}件\n"
        f"**投票記録:** {vote_record_count:,}件\n"
        f"**質問主意書:** {wq_count:,}件\n"
        f"**質問品質分析:** {quality_count:,}件\n"
        f"**平均スコア:** {avg_score_str}\n"
        f"**グレード分布:** {grade_line}"
        f"{last_run_line}\n\n"
        f"**データギャップ:**\n{gaps_text}"
    )

    _send_webhook(
        {
            "title": f"📊 デイリー分析レポート (session {session_number})",
            "description": description,
            "color": 0x9B59B6 if gaps else 0x2ECC71,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )

    logger.info(
        f"Analysis report sent: {scored_members}/{total_members} scored, {len(gaps)} gaps found"
    )
    return 1
