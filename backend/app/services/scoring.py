"""スコアリングエンジン

5軸スコア (立法活動/投票行動/政策影響力/透明性/質問品質) を算出し、
パーセンタイルランクで正規化する。
"""

import logging
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.bill import Bill, BillSponsor
from app.models.member import Member
from app.models.score import MemberScore
from app.models.session import DietSession
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore
from app.models.vote import VoteRecord, VoteResult

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {
    "legislative_activity": 0.25,
    "voting_behavior": 0.20,
    "policy_influence": 0.20,
    "transparency": 0.15,
    "question_quality": 0.20,
}

SPEECH_DENSITY_BASELINE = 3000  # 基準文字数/回
DENSITY_CAP = 2.0


def compute_scores_for_session(db: Session, session_number: int) -> int:
    """指定会期の全議員のスコアを算出する。"""
    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        logger.error(f"Session {session_number} not found")
        return 0

    members = db.query(Member).all()
    if not members:
        logger.warning("No members found")
        return 0

    logger.info(f"Computing scores for {len(members)} members in session {session_number}")

    # Phase 0: 質問品質の集約スコアを事前計算
    quality_scores = _compute_quality_scores_bulk(db, diet_session)

    # Phase 1: raw スコア算出
    raw_scores: dict[int, dict] = {}
    for member in members:
        raw = _compute_raw_scores(db, member, diet_session, quality_scores)
        raw_scores[member.id] = raw

    # Phase 2: パーセンタイルランク正規化 (比較群: chamber × role_category)
    groups: dict[tuple, list[int]] = defaultdict(list)
    for member in members:
        key = (member.chamber, member.role_category or "unknown")
        groups[key].append(member.id)

    normalized_scores: dict[int, dict] = {}
    for group_key, member_ids in groups.items():
        _normalize_group(raw_scores, member_ids, normalized_scores)

    # Phase 3: 総合スコア算出 + DB保存
    count = 0
    for member in members:
        mid = member.id
        if mid not in normalized_scores:
            continue

        raw = raw_scores[mid]
        norm = normalized_scores[mid]

        total = compute_total(norm)
        grade = compute_grade(total)
        breakdown = raw.get("breakdown", {})

        # upsert
        existing = (
            db.query(MemberScore).filter_by(member_id=mid, session_id=diet_session.id).first()
        )
        if existing:
            existing.legislative_activity_raw = raw["legislative_activity"]
            existing.voting_behavior_raw = raw["voting_behavior"]
            existing.policy_influence_raw = raw["policy_influence"]
            existing.transparency_raw = raw["transparency"]
            existing.question_quality_raw = raw["question_quality"]
            existing.legislative_activity = norm["legislative_activity"]
            existing.voting_behavior = norm["voting_behavior"]
            existing.policy_influence = norm["policy_influence"]
            existing.transparency = norm["transparency"]
            existing.question_quality = norm["question_quality"]
            existing.total = total
            existing.grade = grade
            existing.breakdown = breakdown
        else:
            score = MemberScore(
                member_id=mid,
                session_id=diet_session.id,
                legislative_activity_raw=raw["legislative_activity"],
                voting_behavior_raw=raw["voting_behavior"],
                policy_influence_raw=raw["policy_influence"],
                transparency_raw=raw["transparency"],
                question_quality_raw=raw["question_quality"],
                legislative_activity=norm["legislative_activity"],
                voting_behavior=norm["voting_behavior"],
                policy_influence=norm["policy_influence"],
                transparency=norm["transparency"],
                question_quality=norm["question_quality"],
                total=total,
                grade=grade,
                breakdown=breakdown,
            )
            db.add(score)
        count += 1

    db.commit()
    logger.info(f"Computed scores for {count} members")
    return count


def _compute_raw_scores(
    db: Session,
    member: Member,
    session: DietSession,
    quality_scores: dict[int, tuple[float, int]] | None = None,
) -> dict:
    """個別議員のraw スコアを算出する。"""
    las_raw, las_breakdown = _compute_legislative_activity(db, member, session)
    vbs_raw, vbs_breakdown = _compute_voting_behavior(db, member, session)
    pis_raw, pis_breakdown = _compute_policy_influence(db, member, session)
    ts_raw, ts_breakdown = _compute_transparency(db, member, session)
    qq_raw, qq_breakdown = _compute_question_quality(member, quality_scores)

    return {
        "legislative_activity": las_raw,
        "voting_behavior": vbs_raw,
        "policy_influence": pis_raw,
        "transparency": ts_raw,
        "question_quality": qq_raw,
        "breakdown": {
            "legislative_activity": las_breakdown,
            "voting_behavior": vbs_breakdown,
            "policy_influence": pis_breakdown,
            "transparency": ts_breakdown,
            "question_quality": qq_breakdown,
        },
    }


def _compute_legislative_activity(
    db: Session, member: Member, session: DietSession
) -> tuple[float, dict]:
    """立法活動スコア (LAS)"""
    # 法案発議
    sponsorships = (
        db.query(BillSponsor)
        .join(Bill)
        .filter(
            BillSponsor.member_id == member.id,
            Bill.session_id == session.id,
        )
        .all()
    )

    bill_score = 0.0
    bills_sponsored = []
    for sp in sponsorships:
        bill = sp.bill
        # 共同発議者数を取得
        co_count = (
            db.query(func.count(BillSponsor.id)).filter(BillSponsor.bill_id == bill.id).scalar()
        )
        weight = _sponsor_weight(sp.sponsor_type, co_count)

        # LAS は発議の「量」のみ。成立の「質」は PIS で評価。
        score = weight
        bill_score += score

        bills_sponsored.append(
            {
                "bill_id": bill.id,
                "title": bill.title,
                "sponsor_type": sp.sponsor_type,
                "co_sponsors": co_count,
                "weight": weight,
                "score": round(score, 2),
            }
        )

    # 委員会質疑
    speeches = (
        db.query(Speech)
        .filter(
            Speech.member_id == member.id,
            Speech.session_id == session.id,
        )
        .all()
    )
    speech_count = len(speeches)
    total_chars = sum(s.speech_chars for s in speeches)
    avg_chars = total_chars / speech_count if speech_count > 0 else 0

    density_factor = (
        min(avg_chars / SPEECH_DENSITY_BASELINE, DENSITY_CAP) if speech_count > 0 else 0
    )
    committee_score = speech_count * density_factor

    las_raw = bill_score + committee_score

    breakdown = {
        "bill_score": round(bill_score, 2),
        "committee_score": round(committee_score, 2),
        "bills_sponsored": bills_sponsored,
        "speech_count": speech_count,
        "total_speech_chars": total_chars,
        "avg_speech_chars": round(avg_chars, 0),
        "density_factor": round(density_factor, 2),
    }

    return las_raw, breakdown


def _sponsor_weight(sponsor_type: str, co_count: int) -> float:
    """発議者タイプと共同発議者数に基づく重みを返す。"""
    if sponsor_type == "primary":
        return 1.0
    if co_count <= 5:
        return 0.5
    if co_count <= 20:
        return 0.3
    return 0.1


def _compute_voting_behavior(
    db: Session, member: Member, session: DietSession
) -> tuple[float, dict]:
    """投票行動スコア (VBS)"""
    # この議員の投票記録
    records = (
        db.query(VoteRecord)
        .join(VoteResult)
        .join(Bill)
        .filter(
            VoteRecord.member_id == member.id,
            Bill.session_id == session.id,
        )
        .all()
    )

    # 投票機会（同じ院の全投票結果数）
    vote_opportunities = (
        db.query(func.count(VoteResult.id))
        .join(Bill)
        .filter(
            Bill.session_id == session.id,
            VoteResult.chamber == member.chamber,
        )
        .scalar()
    ) or 0

    if vote_opportunities == 0:
        return 0.0, {
            "votes_cast": 0,
            "vote_opportunities": 0,
            "participation_rate": 0.0,
        }

    # 棄権は参加カウント、欠席は非参加
    votes_cast = sum(1 for r in records if r.vote != "absent")
    participation_rate = votes_cast / vote_opportunities * 100

    # 投票内容の比率（将来の党議拘束分析の準備）
    aye_count = sum(1 for r in records if r.vote == "aye")
    nay_count = sum(1 for r in records if r.vote == "nay")
    abstain_count = sum(1 for r in records if r.vote == "abstain")
    absent_count = sum(1 for r in records if r.vote == "absent")
    total_records = len(records)

    aye_rate = (aye_count / total_records * 100) if total_records > 0 else 0.0
    nay_rate = (nay_count / total_records * 100) if total_records > 0 else 0.0

    breakdown = {
        "votes_cast": votes_cast,
        "vote_opportunities": vote_opportunities,
        "participation_rate": round(participation_rate, 1),
        "absent_count": absent_count,
        "abstain_count": abstain_count,
        "aye_count": aye_count,
        "nay_count": nay_count,
        "aye_rate": round(aye_rate, 1),
        "nay_rate": round(nay_rate, 1),
    }

    return participation_rate, breakdown


def _compute_policy_influence(
    db: Session, member: Member, session: DietSession
) -> tuple[float, dict]:
    """政策影響力スコア (PIS)"""
    # 発議した成立法案
    enacted_sponsorships = (
        db.query(BillSponsor)
        .join(Bill)
        .filter(
            BillSponsor.member_id == member.id,
            Bill.session_id == session.id,
            Bill.result.ilike("%成立%"),
        )
        .all()
    )

    enacted_score = 0.0
    enacted_bills = []
    for sp in enacted_sponsorships:
        bill = sp.bill
        kind_weight = _bill_kind_weight(bill.title, bill.bill_kind)
        enacted_score += kind_weight
        enacted_bills.append(
            {
                "bill_id": bill.id,
                "title": bill.title,
                "kind_weight": kind_weight,
            }
        )

    # MVP段階では質問主意書は未実装（データソース追加後に対応）
    pis_raw = enacted_score

    breakdown = {
        "enacted_bills": enacted_bills,
        "enacted_score": round(enacted_score, 2),
        "enacted_count": len(enacted_bills),
    }

    return pis_raw, breakdown


def _bill_kind_weight(title: str, bill_kind: str) -> float:
    """法案の種類に基づく重みを返す。

    閣法は重要度高（1.0）、衆法/参法は 0.8。
    改正法案は種類に応じて減額。
    """
    title_str = title or ""
    kind = bill_kind or ""

    # 法案種別による基本ウェイト
    if kind == "閣法":
        base = 1.0
    else:
        # 衆法 / 参法 / その他
        base = 0.8

    # 改正法案の場合は減額
    if "改正" not in title_str:
        return base  # 新規立法
    if any(kw in title_str for kw in ["一部改正", "軽微", "整備"]):
        return base * 0.3  # 軽微改正
    return base * 0.7  # 大規模改正


def _compute_transparency(db: Session, member: Member, session: DietSession) -> tuple[float, dict]:
    """透明性スコア (TS) - 多様な委員会への参加率

    発言した会議のユニーク数 / 全会議のユニーク数（会期内）で算出。
    多くの種類の委員会に参加している議員ほど高スコア。
    """
    # この議員が発言した会議のユニーク数
    member_meetings = (
        db.query(func.count(func.distinct(Speech.meeting_name)))
        .filter(
            Speech.member_id == member.id,
            Speech.session_id == session.id,
        )
        .scalar()
    ) or 0

    # 全会議のユニーク数（会期内の全議員）
    total_meetings = (
        db.query(func.count(func.distinct(Speech.meeting_name)))
        .filter(Speech.session_id == session.id)
        .scalar()
    ) or 1  # ゼロ除算防止

    diversity_rate = member_meetings / total_meetings * 100

    breakdown = {
        "member_meetings": member_meetings,
        "total_meetings": total_meetings,
        "diversity_rate": round(diversity_rate, 1),
    }

    return diversity_rate, breakdown


def _compute_quality_scores_bulk(db: Session, session: DietSession) -> dict[int, tuple[float, int]]:
    """会期内の全議員の質問品質集約スコアを一括取得する。

    Returns:
        {member_id: (avg_quality, analyzed_count)}
    """
    results = (
        db.query(
            SpeechQualityScore.member_id,
            func.avg(SpeechQualityScore.overall_quality).label("avg_quality"),
            func.count(SpeechQualityScore.id).label("analyzed_count"),
        )
        .filter(SpeechQualityScore.session_id == session.id)
        .group_by(SpeechQualityScore.member_id)
        .all()
    )
    return {row.member_id: (float(row.avg_quality), int(row.analyzed_count)) for row in results}


def _compute_question_quality(
    member: Member,
    quality_scores: dict[int, tuple[float, int]] | None = None,
) -> tuple[float, dict]:
    """質問品質スコア (QQS) — LLM分析結果の集約値。

    speech_quality パイプラインで事前に分析された結果を使用する。
    未分析の場合は 0.0 を返す。
    """
    if not quality_scores or member.id not in quality_scores:
        return 0.0, {"avg_quality": 0.0, "analyzed_speeches": 0}

    avg_quality, count = quality_scores[member.id]
    return avg_quality, {
        "avg_quality": round(avg_quality, 1),
        "analyzed_speeches": count,
    }


def _normalize_group(
    raw_scores: dict[int, dict],
    member_ids: list[int],
    normalized_scores: dict[int, dict],
):
    """比較群内でパーセンタイルランク正規化する。

    同点の議員には平均ランク方式で同一パーセンタイルを付与。
    最高値は100に到達する（rank / (n-1) * 100）。
    """
    axes = [
        "legislative_activity",
        "voting_behavior",
        "policy_influence",
        "transparency",
        "question_quality",
    ]

    for axis in axes:
        values = [(mid, raw_scores[mid][axis]) for mid in member_ids if mid in raw_scores]
        if not values:
            continue

        sorted_values = sorted(values, key=lambda x: x[1])
        n = len(sorted_values)

        if n == 1:
            mid = sorted_values[0][0]
            if mid not in normalized_scores:
                normalized_scores[mid] = {}
            normalized_scores[mid][axis] = 50.0
            continue

        # 同点グループに平均ランクを付与
        rank_map: dict[int, float] = {}
        i = 0
        while i < n:
            j = i
            # 同じスコアの範囲を探す
            while j < n and sorted_values[j][1] == sorted_values[i][1]:
                j += 1
            # i..j-1 が同点グループ。平均ランクを計算
            avg_rank = sum(range(i, j)) / (j - i)
            for k in range(i, j):
                mid = sorted_values[k][0]
                rank_map[mid] = avg_rank
            i = j

        for mid, avg_rank in rank_map.items():
            if mid not in normalized_scores:
                normalized_scores[mid] = {}
            percentile = (avg_rank / (n - 1)) * 100
            normalized_scores[mid][axis] = round(percentile, 1)


def compute_total(normalized: dict, weights: dict | None = None) -> float:
    """正規化スコアから総合スコアを算出する。"""
    w = weights or DEFAULT_WEIGHTS
    total = (
        normalized.get("legislative_activity", 0) * w["legislative_activity"]
        + normalized.get("voting_behavior", 0) * w["voting_behavior"]
        + normalized.get("policy_influence", 0) * w["policy_influence"]
        + normalized.get("transparency", 0) * w["transparency"]
        + normalized.get("question_quality", 0) * w["question_quality"]
    )
    return round(total, 1)


def compute_grade(total: float) -> str:
    """総合スコアからグレードを判定する。"""
    if total >= 80:
        return "A"
    if total >= 60:
        return "B"
    if total >= 40:
        return "C"
    if total >= 20:
        return "D"
    return "F"
