"""バイアス検出パイプライン

スコア分布の偏りを検出し、設計思想（イデオロギー中立・与野党バイアス排除）からの
逸脱をDiscord通知で報告する。

検出対象:
1. 政党別平均スコアの偏り（特定政党が極端に高い/低い）
2. グレード分布の異常（95%がA → インフレ）
3. 軸間の異常な相関（全議員の5軸が同じ → 差別化不足）
4. 大幅なスコア変動（20pt以上の急変）
"""

import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.score import MemberScore
from app.models.score_audit import ScoreAuditLog
from app.models.session import DietSession
from app.pipeline.notify import _send_webhook

logger = logging.getLogger(__name__)

# 閾値
PARTY_SCORE_DIFF_THRESHOLD = 15.0  # 政党間平均スコア差がこれ以上なら警告
GRADE_DOMINANCE_THRESHOLD = 0.6    # 単一グレードが60%以上なら分布異常
LARGE_SCORE_CHANGE_THRESHOLD = 20.0  # 20pt以上変動は要調査
MIN_PARTY_MEMBERS = 3               # 統計に含める最低議員数


def detect_bias(db: Session, session_number: int) -> list[str]:
    """バイアス検出を実行し、警告リストを返す。"""
    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        logger.warning(f"Session {session_number} not found")
        return []

    warnings: list[str] = []

    # --- 1. 政党別平均スコアの偏り ---
    party_warnings = _check_party_bias(db, diet_session)
    warnings.extend(party_warnings)

    # --- 2. グレード分布の異常 ---
    grade_warnings = _check_grade_distribution(db, diet_session)
    warnings.extend(grade_warnings)

    # --- 3. 大幅なスコア変動 ---
    change_warnings = _check_large_score_changes(db, session_number)
    warnings.extend(change_warnings)

    # --- 4. 院別バイアス ---
    chamber_warnings = _check_chamber_bias(db, diet_session)
    warnings.extend(chamber_warnings)

    return warnings


def _check_party_bias(db: Session, session: DietSession) -> list[str]:
    """政党別の平均スコア差をチェック。"""
    results = (
        db.query(
            Member.party,
            func.avg(MemberScore.total).label("avg_score"),
            func.count(MemberScore.id).label("count"),
        )
        .join(MemberScore, MemberScore.member_id == Member.id)
        .filter(MemberScore.session_id == session.id)
        .group_by(Member.party)
        .having(func.count(MemberScore.id) >= MIN_PARTY_MEMBERS)
        .all()
    )

    if len(results) < 2:
        return []

    warnings = []
    scores = [(r.party or "無所属", float(r.avg_score), int(r.count)) for r in results]
    scores.sort(key=lambda x: x[1], reverse=True)

    highest = scores[0]
    lowest = scores[-1]
    diff = highest[1] - lowest[1]

    if diff > PARTY_SCORE_DIFF_THRESHOLD:
        warnings.append(
            f"⚠️ 政党間バイアスの可能性: "
            f"{highest[0]}(平均{highest[1]:.1f}, {highest[2]}名) vs "
            f"{lowest[0]}(平均{lowest[1]:.1f}, {lowest[2]}名) — 差{diff:.1f}pt"
        )

    return warnings


def _check_grade_distribution(db: Session, session: DietSession) -> list[str]:
    """グレード分布の異常検出。"""
    results = (
        db.query(
            MemberScore.grade,
            func.count(MemberScore.id).label("count"),
        )
        .filter(MemberScore.session_id == session.id)
        .group_by(MemberScore.grade)
        .all()
    )

    if not results:
        return []

    total = sum(r.count for r in results)
    if total == 0:
        return []

    warnings = []
    for r in results:
        ratio = r.count / total
        if ratio > GRADE_DOMINANCE_THRESHOLD:
            warnings.append(
                f"⚠️ グレード分布異常: {r.grade}グレードが{ratio:.0%} ({r.count}/{total}) — "
                "スコアインフレ/デフレの可能性"
            )

    return warnings


def _check_large_score_changes(db: Session, session_number: int) -> list[str]:
    """大幅なスコア変動の検出。"""
    audits = (
        db.query(ScoreAuditLog)
        .filter(
            ScoreAuditLog.session_number == session_number,
            ScoreAuditLog.prev_total.isnot(None),
            func.abs(ScoreAuditLog.diff_total) > LARGE_SCORE_CHANGE_THRESHOLD,
        )
        .order_by(func.abs(ScoreAuditLog.diff_total).desc())
        .limit(10)
        .all()
    )

    if not audits:
        return []

    warnings = []
    for audit in audits:
        member = db.query(Member).filter_by(id=audit.member_id).first()
        name = member.name if member else f"ID:{audit.member_id}"
        direction = "上昇" if audit.diff_total > 0 else "下降"
        warnings.append(
            f"⚠️ 大幅スコア変動: {name} ({audit.prev_total:.1f}→{audit.new_total:.1f}, "
            f"{audit.diff_total:+.1f}pt {direction})"
        )

    return warnings


def _check_chamber_bias(db: Session, session: DietSession) -> list[str]:
    """衆議院と参議院のスコア分布差をチェック。"""
    results = (
        db.query(
            Member.chamber,
            func.avg(MemberScore.total).label("avg_score"),
            func.count(MemberScore.id).label("count"),
        )
        .join(MemberScore, MemberScore.member_id == Member.id)
        .filter(MemberScore.session_id == session.id)
        .group_by(Member.chamber)
        .all()
    )

    if len(results) < 2:
        return []

    warnings = []
    chambers = {r.chamber: (float(r.avg_score), int(r.count)) for r in results}

    if "representatives" in chambers and "councillors" in chambers:
        rep_avg = chambers["representatives"][0]
        cou_avg = chambers["councillors"][0]
        diff = abs(rep_avg - cou_avg)

        if diff > PARTY_SCORE_DIFF_THRESHOLD:
            warnings.append(
                f"⚠️ 院別バイアスの可能性: "
                f"衆議院(平均{rep_avg:.1f}) vs 参議院(平均{cou_avg:.1f}) — 差{diff:.1f}pt"
            )

    return warnings


def run_bias_detection(db: Session, session_number: int) -> int:
    """バイアス検出を実行しDiscord通知を送信する。"""
    warnings = detect_bias(db, session_number)

    if warnings:
        description = (
            f"**会期:** {session_number}\n"
            f"**検出件数:** {len(warnings)}\n\n"
            + "\n".join(warnings)
        )
        _send_webhook({
            "title": "🔍 バイアス検出レポート",
            "description": description,
            "color": 0xE74C3C,
        })
        logger.warning(f"Bias detection: {len(warnings)} warnings for session {session_number}")
    else:
        _send_webhook({
            "title": "✅ バイアス検出: 問題なし",
            "description": f"会期 {session_number} のスコア分布に異常は検出されませんでした。",
            "color": 0x2ECC71,
        })
        logger.info(f"Bias detection: no issues for session {session_number}")

    return len(warnings)
