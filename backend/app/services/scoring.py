"""スコアリングエンジン

5軸スコア (立法活動/投票行動/政策影響力/透明性/質問品質) を算出し、
パーセンタイルランクで正規化する。
"""

import logging
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.bill import Bill, BillSponsor
from app.models.committee import CommitteeMembership
from app.models.member import Member
from app.models.political_fund import PoliticalFund
from app.models.score import MemberScore
from app.models.score_audit import ScoreAuditLog
from app.models.session import DietSession
from app.models.sleeping_detection import SleepingDetection
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore
from app.models.vote import VoteRecord, VoteResult
from app.models.weight_version import WeightVersion
from app.models.written_question import WrittenQuestion

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
SLEEPING_PENALTY_PER_INCIDENT = 3.0  # 承認済み居眠り1件あたりのペナルティ（totalから減算）
SLEEPING_PENALTY_CAP = 15.0  # 居眠りペナルティ上限


def _get_active_weights(db: Session) -> tuple[dict, str | None]:
    """DBからアクティブな重みバージョンを取得する。

    Returns:
        (weights_dict, version_string) — DBにない場合は (DEFAULT_WEIGHTS, None)
    """
    active = (
        db.query(WeightVersion)
        .filter(WeightVersion.is_active.is_(True))
        .order_by(WeightVersion.created_at.desc())
        .first()
    )
    if not active:
        logger.info("No active weight version in DB, using DEFAULT_WEIGHTS")
        return DEFAULT_WEIGHTS, None

    weights = {
        "legislative_activity": active.legislative_activity,
        "voting_behavior": active.voting_behavior,
        "policy_influence": active.policy_influence,
        "transparency": active.transparency,
        "question_quality": active.question_quality,
    }
    logger.info(f"Using weight version: {active.version}")
    return weights, active.version


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

    # Phase 0: 重みバージョン取得
    weights, weights_version = _get_active_weights(db)

    # Phase 0.5: 質問品質の集約スコアを事前計算
    quality_scores = _compute_quality_scores_bulk(db, diet_session)

    # Phase 0.6: 居眠りペナルティ事前計算
    sleeping_penalties = _compute_sleeping_penalties_bulk(db, diet_session)

    # Phase 0.7: 委員会所属データの一括取得
    committee_data = _compute_committee_data_bulk(db, diet_session)

    # Phase 0.8: 政治資金データの一括取得
    fund_data = _compute_fund_data_bulk(db)

    # Phase 1: raw スコア算出
    raw_scores: dict[int, dict] = {}
    for member in members:
        raw = _compute_raw_scores(
            db, member, diet_session, quality_scores, committee_data, fund_data
        )
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

        total = compute_total(norm, weights)

        # 居眠りペナルティ適用
        sleeping_info = sleeping_penalties.get(mid)
        if sleeping_info:
            penalty = sleeping_info["penalty"]
            total = max(0.0, round(total - penalty, 1))
            breakdown_sleeping = {
                "approved_incidents": sleeping_info["count"],
                "total_duration_sec": sleeping_info["total_duration"],
                "penalty_applied": penalty,
            }
        else:
            breakdown_sleeping = None

        grade = compute_grade(total)
        breakdown = raw.get("breakdown", {})
        if breakdown_sleeping:
            breakdown["sleeping_penalty"] = breakdown_sleeping

        # upsert
        existing = (
            db.query(MemberScore).filter_by(member_id=mid, session_id=diet_session.id).first()
        )

        # 監査ログ: before 値を記録
        audit = ScoreAuditLog(
            member_id=mid,
            session_number=session_number,
            prev_total=existing.total if existing else None,
            prev_grade=existing.grade if existing else None,
            prev_legislative_activity=existing.legislative_activity if existing else None,
            prev_voting_behavior=existing.voting_behavior if existing else None,
            prev_policy_influence=existing.policy_influence if existing else None,
            prev_transparency=existing.transparency if existing else None,
            prev_question_quality=existing.question_quality if existing else None,
            new_total=total,
            new_grade=grade,
            new_legislative_activity=norm["legislative_activity"],
            new_voting_behavior=norm["voting_behavior"],
            new_policy_influence=norm["policy_influence"],
            new_transparency=norm["transparency"],
            new_question_quality=norm["question_quality"],
            diff_total=round(total - existing.total, 1) if existing else 0.0,
            reason="scheduled_pipeline",
            weights_version=weights_version,
        )
        db.add(audit)

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
    committee_data: dict[int, dict] | None = None,
    fund_data: dict[int, dict] | None = None,
) -> dict:
    """個別議員のraw スコアを算出する。"""
    las_raw, las_breakdown = _compute_legislative_activity(
        db, member, session, committee_data
    )
    vbs_raw, vbs_breakdown = _compute_voting_behavior(db, member, session)
    pis_raw, pis_breakdown = _compute_policy_influence(db, member, session)
    ts_raw, ts_breakdown = _compute_transparency(db, member, session, fund_data)
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


COMMITTEE_ROLE_WEIGHT = {
    "委員長": 2.0,
    "理事": 1.5,
    "委員": 1.0,
}
COMMITTEE_MEMBERSHIP_WEIGHT = 0.5  # 委員会所属1件あたりの加算
COMMITTEE_LEADERSHIP_BONUS = 1.0  # 委員長・理事へのボーナス


def _compute_legislative_activity(
    db: Session, member: Member, session: DietSession,
    committee_data: dict[int, dict] | None = None,
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
        co_count = (
            db.query(func.count(BillSponsor.id)).filter(BillSponsor.bill_id == bill.id).scalar()
        )
        weight = _sponsor_weight(sp.sponsor_type, co_count)
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
    speech_score = speech_count * density_factor

    # 質問主意書
    wq_count = (
        db.query(func.count(WrittenQuestion.id))
        .filter(
            WrittenQuestion.member_id == member.id,
            WrittenQuestion.session_id == session.id,
        )
        .scalar()
    ) or 0
    wq_answered = (
        db.query(func.count(WrittenQuestion.id))
        .filter(
            WrittenQuestion.member_id == member.id,
            WrittenQuestion.session_id == session.id,
            WrittenQuestion.has_answer.is_(True),
        )
        .scalar()
    ) or 0
    wq_score = wq_count * 0.5

    # 委員会所属スコア
    cm_score = 0.0
    cm_count = 0
    cm_leadership = 0
    if committee_data and member.id in committee_data:
        cm_info = committee_data[member.id]
        cm_count = cm_info["count"]
        cm_leadership = cm_info["leadership_count"]
        cm_score = cm_count * COMMITTEE_MEMBERSHIP_WEIGHT + cm_leadership * COMMITTEE_LEADERSHIP_BONUS

    las_raw = bill_score + speech_score + wq_score + cm_score

    breakdown = {
        "bill_score": round(bill_score, 2),
        "committee_score": round(speech_score, 2),
        "written_questions_score": round(wq_score, 2),
        "committee_membership_score": round(cm_score, 2),
        "bills_sponsored": bills_sponsored,
        "speech_count": speech_count,
        "total_speech_chars": total_chars,
        "avg_speech_chars": round(avg_chars, 0),
        "density_factor": round(density_factor, 2),
        "written_questions": wq_count,
        "written_questions_answered": wq_answered,
        "committees_count": cm_count,
        "committees_leadership": cm_leadership,
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

    # 質問主意書（答弁ありは政策対話の成果）
    wq_answered_count = (
        db.query(func.count(WrittenQuestion.id))
        .filter(
            WrittenQuestion.member_id == member.id,
            WrittenQuestion.session_id == session.id,
            WrittenQuestion.has_answer.is_(True),
        )
        .scalar()
    ) or 0
    # 答弁付き質問主意書1件 = 0.3ポイント
    wq_influence = wq_answered_count * 0.3

    pis_raw = enacted_score + wq_influence

    breakdown = {
        "enacted_bills": enacted_bills,
        "enacted_score": round(enacted_score, 2),
        "enacted_count": len(enacted_bills),
        "written_questions_answered": wq_answered_count,
        "written_questions_influence": round(wq_influence, 2),
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


FUND_TRANSPARENCY_WEIGHT = 0.3  # 政治資金データの透明性への寄与率


def _compute_transparency(
    db: Session, member: Member, session: DietSession,
    fund_data: dict[int, dict] | None = None,
) -> tuple[float, dict]:
    """透明性スコア (TS) - 多様な委員会への参加率 + 政治資金の透明性

    1. 活動多様性: 発言した会議の種類の広さ（0-100）
    2. 資金透明性: 政治資金の個人献金比率・使途明確性（0-100）

    最終スコア = 活動多様性 × (1 - fund_weight) + 資金透明性 × fund_weight
    """
    # 活動多様性: この議員が発言した会議のユニーク数
    member_meetings = (
        db.query(func.count(func.distinct(Speech.meeting_name)))
        .filter(
            Speech.member_id == member.id,
            Speech.session_id == session.id,
        )
        .scalar()
    ) or 0

    total_meetings = (
        db.query(func.count(func.distinct(Speech.meeting_name)))
        .filter(Speech.session_id == session.id)
        .scalar()
    ) or 1

    diversity_rate = member_meetings / total_meetings * 100

    # 資金透明性
    fund_score = 0.0
    fund_breakdown = {}

    if fund_data and member.id in fund_data:
        fi = fund_data[member.id]
        fund_score = fi["transparency_score"]
        fund_breakdown = {
            "total_income": fi["total_income"],
            "individual_ratio": fi["individual_ratio"],
            "corporate_ratio": fi["corporate_ratio"],
            "fundraising_ratio": fi["fundraising_ratio"],
            "research_ratio": fi["research_ratio"],
            "fund_transparency_score": round(fund_score, 1),
        }

    # 政治資金データがある場合のみブレンド
    if fund_data and member.id in fund_data:
        ts_raw = diversity_rate * (1 - FUND_TRANSPARENCY_WEIGHT) + fund_score * FUND_TRANSPARENCY_WEIGHT
    else:
        ts_raw = diversity_rate

    breakdown = {
        "member_meetings": member_meetings,
        "total_meetings": total_meetings,
        "diversity_rate": round(diversity_rate, 1),
        **fund_breakdown,
    }

    return ts_raw, breakdown


def _compute_sleeping_penalties_bulk(
    db: Session, session: DietSession
) -> dict[int, dict]:
    """会期内の承認済み居眠り検出からペナルティを一括計算する。

    Returns:
        {member_id: {"count": int, "total_duration": float, "penalty": float}}
    """
    try:
        results = (
            db.query(
                SleepingDetection.member_id,
                func.count(SleepingDetection.id).label("incident_count"),
                func.sum(SleepingDetection.duration_sec).label("total_duration"),
            )
            .filter(
                SleepingDetection.session_id == session.id,
                SleepingDetection.review_status == "approved",
                SleepingDetection.member_id.isnot(None),
            )
            .group_by(SleepingDetection.member_id)
            .all()
        )
        penalties = {}
        for row in results:
            raw_penalty = row.incident_count * SLEEPING_PENALTY_PER_INCIDENT
            penalty = min(raw_penalty, SLEEPING_PENALTY_CAP)
            penalties[row.member_id] = {
                "count": int(row.incident_count),
                "total_duration": float(row.total_duration),
                "penalty": round(penalty, 1),
            }
        return penalties
    except Exception:
        db.rollback()
        logger.info("sleeping_detections table not available, skipping sleeping penalties")
        return {}


def _compute_quality_scores_bulk(db: Session, session: DietSession) -> dict[int, tuple[float, int]]:
    """会期内の全議員の質問品質集約スコアを一括取得する。

    Returns:
        {member_id: (avg_quality, analyzed_count)}
    """
    try:
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
    except Exception:
        db.rollback()
        logger.info("speech_quality_scores table not available, skipping quality scores")
        return {}


def _compute_committee_data_bulk(
    db: Session, session: DietSession
) -> dict[int, dict]:
    """会期内の全議員の委員会所属データを一括取得する。

    Returns:
        {member_id: {"count": int, "leadership_count": int, "committees": list}}
    """
    try:
        memberships = (
            db.query(CommitteeMembership)
            .filter(CommitteeMembership.session_id == session.id)
            .all()
        )
        result: dict[int, dict] = {}
        for cm in memberships:
            if cm.member_id not in result:
                result[cm.member_id] = {
                    "count": 0,
                    "leadership_count": 0,
                    "committees": [],
                }
            info = result[cm.member_id]
            info["count"] += 1
            if cm.role in ("委員長", "理事"):
                info["leadership_count"] += 1
            info["committees"].append(cm.committee_name)
        return result
    except Exception:
        db.rollback()
        logger.info("committee_memberships table not available, skipping committee data")
        return {}


def _compute_fund_data_bulk(db: Session) -> dict[int, dict]:
    """全議員の政治資金データを一括取得し、透明性スコアを計算する。

    透明性スコアの評価基準:
    - 個人献金比率が高い → 透明性が高い（市民からの支持）
    - 企業献金・パーティー券依存度が低い → 透明性が高い
    - 調査研究費比率が高い → 政策立案に投資している
    - 収支報告書が存在する → 基本的な透明性

    Returns:
        {member_id: {"transparency_score": float, ...}}
    """
    try:
        # 最新年度のデータを取得（議員ごとに団体を合算）
        funds = db.query(PoliticalFund).all()
        if not funds:
            return {}

        # 議員ごとに最新年度の合算
        member_funds: dict[int, dict] = {}
        for f in funds:
            mid = f.member_id
            if mid not in member_funds:
                member_funds[mid] = {
                    "latest_year": f.report_year,
                    "total_income": 0.0,
                    "individual_donations": 0.0,
                    "corporate_donations": 0.0,
                    "fundraising_party": 0.0,
                    "total_expenditure": 0.0,
                    "research_expenses": 0.0,
                    "political_activity": 0.0,
                }
            info = member_funds[mid]
            # 同一年度または最新年度のデータを合算
            if f.report_year >= info["latest_year"]:
                if f.report_year > info["latest_year"]:
                    # より新しい年度が見つかった場合はリセット
                    info["latest_year"] = f.report_year
                    for key in list(info.keys()):
                        if key != "latest_year":
                            info[key] = 0.0
                info["total_income"] += f.total_income
                info["individual_donations"] += f.individual_donations
                info["corporate_donations"] += f.corporate_donations
                info["fundraising_party"] += f.fundraising_party
                info["total_expenditure"] += f.total_expenditure
                info["research_expenses"] += f.research_expenses
                info["political_activity"] += f.political_activity

        result: dict[int, dict] = {}
        for mid, info in member_funds.items():
            income = info["total_income"]
            if income <= 0:
                # 収入0の場合、報告書が存在するだけで基本点
                result[mid] = {
                    "transparency_score": 30.0,
                    "total_income": 0.0,
                    "individual_ratio": 0.0,
                    "corporate_ratio": 0.0,
                    "fundraising_ratio": 0.0,
                    "research_ratio": 0.0,
                }
                continue

            individual_ratio = info["individual_donations"] / income
            corporate_ratio = info["corporate_donations"] / income
            fundraising_ratio = info["fundraising_party"] / income

            expenditure = info["total_expenditure"]
            research_ratio = (
                info["research_expenses"] / expenditure if expenditure > 0 else 0.0
            )

            # 透明性スコア計算 (0-100)
            # 1. 基本点: 報告書が存在する = 30点
            score = 30.0
            # 2. 個人献金比率ボーナス (最大20点)
            score += min(individual_ratio * 100, 20.0)
            # 3. 企業献金・パーティー券低依存ボーナス (最大25点)
            dependency = corporate_ratio + fundraising_ratio
            score += max(0, 25.0 - dependency * 50)
            # 4. 調査研究費比率ボーナス (最大15点)
            score += min(research_ratio * 100, 15.0)
            # 5. 収支バランス（支出が収入の範囲内）(最大10点)
            if expenditure <= income * 1.1:
                score += 10.0
            elif expenditure <= income * 1.5:
                score += 5.0

            score = min(score, 100.0)

            result[mid] = {
                "transparency_score": round(score, 1),
                "total_income": income,
                "individual_ratio": round(individual_ratio, 3),
                "corporate_ratio": round(corporate_ratio, 3),
                "fundraising_ratio": round(fundraising_ratio, 3),
                "research_ratio": round(research_ratio, 3),
            }
        return result
    except Exception:
        db.rollback()
        logger.info("political_funds table not available, skipping fund data")
        return {}


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
