"""E2Eガードレールテスト

実際のDB（SQLite）を使い、パイプライン全体を通して
サービスの設計思想からの逸脱を検知する。モック不使用。

検証対象:
1. スコアリングパイプラインE2E — 生データ→正規化→総合→グレード→DB保存
2. 監査ログの完全性 — 全スコア変更に対してaudit recordが存在
3. バイアス検出E2E — 偏った分布を実際に検知する
4. 重みバージョン統合 — DB重み変更でスコアが実際に変わる
5. 設計思想不変量 — どんな実装でも必ず成立すべき数学的性質
6. レビューAPI E2E — CRUD + いいね + サマリーの全フロー
"""

from app.models.bill import Bill, BillSponsor
from app.models.member import Member
from app.models.score import MemberScore
from app.models.score_audit import ScoreAuditLog
from app.models.session import DietSession
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore
from app.models.vote import VoteRecord, VoteResult
from app.models.weight_version import WeightVersion
from app.models.written_question import WrittenQuestion
from app.pipeline.bias_detector import detect_bias
from app.services.scoring import (
    DEFAULT_WEIGHTS,
    compute_scores_for_session,
)


def _seed_full_session(db):
    """スコアリングE2E用の完全なテストデータセットを作成する。

    衆議院5名・参議院5名の計10名、各種活動データ付き。
    政党は均等分布（与党系5名・野党系5名）で、バイアスがないことを検証可能。
    """
    session = DietSession(id=1, session_number=215, kind="通常")
    db.add(session)

    members = []
    for i in range(1, 11):
        chamber = "representatives" if i <= 5 else "councillors"
        party = "政党A" if i % 2 == 0 else "政党B"
        m = Member(
            id=i,
            name=f"議員{i:02d}",
            chamber=chamber,
            party=party,
            role_category="member",
        )
        members.append(m)
    db.add_all(members)

    # 各議員に発言データ（量に差をつける）
    speeches = []
    for i, m in enumerate(members, 1):
        # 議員1は10発言、議員2は9発言...議員10は1発言
        count = 11 - i
        for j in range(count):
            s = Speech(
                session_id=1,
                member_id=m.id,
                meeting_name=f"委員会{j % 3 + 1}",
                speech_text=f"テスト発言 {'あ' * 500}",
                speech_chars=500 + j * 100,
            )
            speeches.append(s)
    db.add_all(speeches)

    # 法案 + スポンサーシップ
    bills = []
    sponsors = []
    for i in range(1, 6):
        b = Bill(
            id=i,
            session_id=1,
            bill_kind="衆法",
            title=f"テスト法案{i}",
            result="成立" if i <= 3 else "審議中",
        )
        bills.append(b)
        # 議員i が primary sponsor
        sponsors.append(BillSponsor(bill_id=i, member_id=i, sponsor_type="primary"))
    db.add_all(bills)
    db.flush()
    db.add_all(sponsors)

    # 投票結果 + 投票記録
    for bill in bills[:3]:
        vr = VoteResult(
            bill_id=bill.id,
            chamber="representatives",
            ayes=200,
            nays=100,
            result="可決",
        )
        db.add(vr)
        db.flush()
        # 衆議院メンバーが投票
        for m in members[:5]:
            vote = "aye" if m.id % 2 == 0 else "nay"
            db.add(
                VoteRecord(
                    vote_result_id=vr.id,
                    member_id=m.id,
                    vote=vote,
                )
            )

    # 質問主意書
    for m in members[:3]:
        db.add(
            WrittenQuestion(
                session_id=1,
                member_id=m.id,
                chamber=m.chamber,
                question_number=m.id,
                title=f"質問主意書{m.id}",
                has_answer=True,
            )
        )

    # 発言品質スコア（事前分析済みとして投入）
    speech_list = db.query(Speech).all()
    for s in speech_list:
        # 議員IDに応じて品質に差を出す
        quality = 30 + (s.member_id * 5)
        db.add(
            SpeechQualityScore(
                speech_id=s.id,
                member_id=s.member_id,
                session_id=1,
                policy_relevance=quality,
                constructiveness=quality + 5,
                expertise=quality - 5,
                national_interest=quality,
                overall_quality=quality,
            )
        )

    db.commit()
    return members


# =====================================================================
# 1. スコアリングパイプラインE2E
# =====================================================================


class TestScoringPipelineE2E:
    """生データからスコア計算→DB保存まで全段階を実DBで検証。"""

    def test_compute_scores_produces_results_for_all_members(self, db):
        """全議員にスコアが計算されること。"""
        members = _seed_full_session(db)
        count = compute_scores_for_session(db, 215)

        assert count == len(members)

        scores = db.query(MemberScore).filter_by(session_id=1).all()
        assert len(scores) == len(members)

    def test_all_scores_within_0_100(self, db):
        """全ての正規化スコアが0-100の範囲内であること。"""
        _seed_full_session(db)
        compute_scores_for_session(db, 215)

        scores = db.query(MemberScore).all()
        axes = [
            "legislative_activity",
            "voting_behavior",
            "policy_influence",
            "transparency",
            "question_quality",
        ]
        for s in scores:
            for axis in axes:
                val = getattr(s, axis)
                assert 0.0 <= val <= 100.0, f"member_id={s.member_id} {axis}={val} が0-100範囲外"
            assert 0.0 <= s.total <= 100.0, f"member_id={s.member_id} total={s.total} が0-100範囲外"

    def test_grades_consistent_with_total(self, db):
        """グレードが総合スコアと一致していること。"""
        _seed_full_session(db)
        compute_scores_for_session(db, 215)

        for s in db.query(MemberScore).all():
            if s.total >= 80:
                expected = "A"
            elif s.total >= 60:
                expected = "B"
            elif s.total >= 40:
                expected = "C"
            elif s.total >= 20:
                expected = "D"
            else:
                expected = "F"
            assert s.grade == expected, (
                f"member_id={s.member_id}: total={s.total} "
                f"→ grade should be {expected}, got {s.grade}"
            )

    def test_total_equals_weighted_sum(self, db):
        """総合スコアが重み付き合計と一致すること。"""
        _seed_full_session(db)
        compute_scores_for_session(db, 215)

        for s in db.query(MemberScore).all():
            expected = round(
                s.legislative_activity * DEFAULT_WEIGHTS["legislative_activity"]
                + s.voting_behavior * DEFAULT_WEIGHTS["voting_behavior"]
                + s.policy_influence * DEFAULT_WEIGHTS["policy_influence"]
                + s.transparency * DEFAULT_WEIGHTS["transparency"]
                + s.question_quality * DEFAULT_WEIGHTS["question_quality"],
                1,
            )
            assert abs(s.total - expected) < 0.2, (
                f"member_id={s.member_id}: total={s.total} != weighted_sum={expected}"
            )

    def test_normalization_produces_full_range(self, db):
        """正規化がグループ内で0-100の範囲を使い切ること。

        正規化はchamber × role_categoryグループ内で行われる。
        同点がない軸では、グループ内の最低=0.0、最高=100.0になるべき。
        """
        _seed_full_session(db)
        compute_scores_for_session(db, 215)

        scores = db.query(MemberScore).all()
        # chamber × role_category でグループ分け
        members = {m.id: m for m in db.query(Member).all()}
        groups: dict[tuple, list[MemberScore]] = {}
        for s in scores:
            m = members[s.member_id]
            key = (m.chamber, m.role_category or "unknown")
            groups.setdefault(key, []).append(s)

        for group_key, group_scores in groups.items():
            if len(group_scores) < 2:
                continue
            # legislative_activity はraw scoreに差があるはず
            la_values = [s.legislative_activity for s in group_scores]
            la_raw = [s.legislative_activity_raw for s in group_scores]
            # rawに差がある場合、0.0と100.0が含まれるべき
            if len(set(la_raw)) == len(la_raw):
                assert 0.0 in la_values, f"{group_key} legislative_activity: 最低ランク0.0がない"
                assert 100.0 in la_values, (
                    f"{group_key} legislative_activity: 最高ランク100.0がない"
                )

    def test_same_raw_scores_get_same_normalized(self, db):
        """同じraw scoreの議員は同じ正規化スコアを得ること（公平性）。"""
        session = DietSession(id=1, session_number=215, kind="通常")
        db.add(session)

        # 全く同じ活動量の議員3名
        for i in range(1, 4):
            db.add(
                Member(
                    id=i,
                    name=f"均一議員{i}",
                    chamber="representatives",
                    party=f"政党{i}",
                    role_category="member",
                )
            )
            for j in range(5):
                db.add(
                    Speech(
                        session_id=1,
                        member_id=i,
                        meeting_name="同じ委員会",
                        speech_text="同じ発言 " + "あ" * 500,
                        speech_chars=600,
                    )
                )
        db.commit()

        compute_scores_for_session(db, 215)
        scores = db.query(MemberScore).order_by(MemberScore.member_id).all()
        assert len(scores) == 3

        # 全員同じ正規化スコアを持つべき
        for axis in ["legislative_activity", "transparency"]:
            vals = [getattr(s, axis) for s in scores]
            assert vals[0] == vals[1] == vals[2], (
                f"{axis}: 同じ活動の議員に異なるスコア {vals} → 公平性違反"
            )

    def test_party_independent_scoring(self, db):
        """政党が異なっても同じ活動量なら同じスコアになること。"""
        session = DietSession(id=1, session_number=215, kind="通常")
        db.add(session)

        parties = ["与党A", "野党B", "少数党C"]
        for i, party in enumerate(parties, 1):
            db.add(
                Member(
                    id=i,
                    name=f"議員{i}",
                    chamber="representatives",
                    party=party,
                    role_category="member",
                )
            )
            for j in range(3):
                db.add(
                    Speech(
                        session_id=1,
                        member_id=i,
                        meeting_name=f"委員会{j}",
                        speech_text="同一発言 " + "い" * 400,
                        speech_chars=500,
                    )
                )
        db.commit()
        compute_scores_for_session(db, 215)

        scores = db.query(MemberScore).all()
        totals = {s.member_id: s.total for s in scores}
        # 全員同じtotal
        assert totals[1] == totals[2] == totals[3], (
            f"政党が異なるだけで活動量同一の議員のスコアに差: {totals} → 政党バイアスの可能性"
        )


# =====================================================================
# 2. 監査ログの完全性
# =====================================================================


class TestAuditLogCompleteness:
    """全スコア変更に監査ログが作成されることを検証。"""

    def test_first_scoring_creates_audit_logs(self, db):
        """初回スコアリングで全議員分の監査ログが作成されること。"""
        members = _seed_full_session(db)
        compute_scores_for_session(db, 215)

        audits = db.query(ScoreAuditLog).all()
        assert len(audits) == len(members)

        # 初回はprev_totalがNone
        for a in audits:
            assert a.prev_total is None
            assert a.new_total is not None
            assert a.diff_total == 0.0

    def test_second_scoring_records_diff(self, db):
        """2回目スコアリングでdiff_totalが記録されること。"""
        _seed_full_session(db)
        compute_scores_for_session(db, 215)

        # 活動データを追加して再スコアリング
        db.add(
            Speech(
                session_id=1,
                member_id=1,
                meeting_name="追加委員会",
                speech_text="追加発言 " + "う" * 1000,
                speech_chars=1500,
            )
        )
        db.add(
            SpeechQualityScore(
                speech_id=db.query(Speech).count() + 1,
                member_id=1,
                session_id=1,
                policy_relevance=90,
                constructiveness=90,
                expertise=90,
                national_interest=90,
                overall_quality=90,
            )
        )
        db.commit()
        compute_scores_for_session(db, 215)

        # 2回目の監査ログにはprev_totalが存在
        second_audits = db.query(ScoreAuditLog).filter(ScoreAuditLog.prev_total.isnot(None)).all()
        assert len(second_audits) > 0, "2回目スコアリングで prev_total を持つ監査ログがない"

    def test_audit_log_has_all_axes(self, db):
        """監査ログに5軸全てのbefore/after値が記録されること。"""
        _seed_full_session(db)
        compute_scores_for_session(db, 215)

        audit = db.query(ScoreAuditLog).first()
        assert audit is not None

        # new_* は全て記録されている
        assert audit.new_total is not None
        assert audit.new_grade is not None
        assert audit.new_legislative_activity is not None
        assert audit.new_voting_behavior is not None
        assert audit.new_policy_influence is not None
        assert audit.new_transparency is not None
        assert audit.new_question_quality is not None

    def test_audit_reason_is_recorded(self, db):
        """監査ログにreasonが記録されること。"""
        _seed_full_session(db)
        compute_scores_for_session(db, 215)

        for audit in db.query(ScoreAuditLog).all():
            assert audit.reason, f"member_id={audit.member_id} の監査ログにreasonがない"


# =====================================================================
# 3. バイアス検出E2E
# =====================================================================


class TestBiasDetectionE2E:
    """実際に偏ったデータを作成し、バイアス検出が機能することを検証。"""

    def test_detects_party_bias(self, db):
        """政党間スコア差が大きい場合に警告が出ること。"""
        session = DietSession(id=1, session_number=215, kind="通常")
        db.add(session)

        # 政党Aは全員高スコア、政党Bは全員低スコア
        for i in range(1, 7):
            party = "政党A" if i <= 3 else "政党B"
            total = 85.0 if i <= 3 else 30.0
            db.add(
                Member(
                    id=i,
                    name=f"議員{i}",
                    chamber="representatives",
                    party=party,
                )
            )
            db.add(
                MemberScore(
                    member_id=i,
                    session_id=1,
                    total=total,
                    grade="A" if total >= 80 else "D",
                    legislative_activity=total,
                    voting_behavior=total,
                    policy_influence=total,
                    transparency=total,
                    question_quality=total,
                )
            )
        db.commit()

        warnings = detect_bias(db, 215)
        party_warnings = [w for w in warnings if "政党間バイアス" in w]
        assert len(party_warnings) > 0, "政党間に55ptの差があるのにバイアスが検出されなかった"

    def test_detects_grade_inflation(self, db):
        """全員がAグレードの場合にグレード分布異常が検出されること。"""
        session = DietSession(id=1, session_number=215, kind="通常")
        db.add(session)

        for i in range(1, 11):
            db.add(
                Member(
                    id=i,
                    name=f"議員{i}",
                    chamber="representatives",
                    party=f"政党{i % 3}",
                )
            )
            db.add(
                MemberScore(
                    member_id=i,
                    session_id=1,
                    total=90.0,
                    grade="A",
                    legislative_activity=90,
                    voting_behavior=90,
                    policy_influence=90,
                    transparency=90,
                    question_quality=90,
                )
            )
        db.commit()

        warnings = detect_bias(db, 215)
        grade_warnings = [w for w in warnings if "グレード分布異常" in w]
        assert len(grade_warnings) > 0, (
            "全員Aグレードなのに分布異常が検出されなかった → スコアインフレを見逃す"
        )

    def test_detects_large_score_changes(self, db):
        """大幅なスコア変動が検出されること。"""
        session = DietSession(id=1, session_number=215, kind="通常")
        db.add(session)
        db.add(
            Member(
                id=1,
                name="変動議員",
                chamber="representatives",
                party="政党A",
            )
        )

        # 大幅な変動の監査ログ
        db.add(
            ScoreAuditLog(
                member_id=1,
                session_number=215,
                prev_total=30.0,
                prev_grade="D",
                prev_legislative_activity=30,
                prev_voting_behavior=30,
                prev_policy_influence=30,
                prev_transparency=30,
                prev_question_quality=30,
                new_total=80.0,
                new_grade="A",
                new_legislative_activity=80,
                new_voting_behavior=80,
                new_policy_influence=80,
                new_transparency=80,
                new_question_quality=80,
                diff_total=50.0,
                reason="test",
            )
        )
        db.commit()

        warnings = detect_bias(db, 215)
        change_warnings = [w for w in warnings if "大幅スコア変動" in w]
        assert len(change_warnings) > 0, "50pt変動があるのに検出されなかった"

    def test_no_false_positive_on_fair_distribution(self, db):
        """均等な分布ではバイアス警告が出ないこと。"""
        _seed_full_session(db)
        compute_scores_for_session(db, 215)

        warnings = detect_bias(db, 215)
        party_warnings = [w for w in warnings if "政党間バイアス" in w]
        # 均等な活動データなら政党バイアスは出ないはず
        # （同じ政党内でも活動量に差があるため、ノイズはあり得る）
        assert len(party_warnings) == 0, f"均等分布なのに政党バイアス警告: {party_warnings}"


# =====================================================================
# 4. 重みバージョン統合E2E
# =====================================================================


class TestWeightVersionIntegrationE2E:
    """DB重みの変更がスコア計算に反映されることを検証。"""

    def test_db_weights_override_default(self, db):
        """DBのアクティブ重みがDEFAULT_WEIGHTSを上書きすること。"""
        _seed_full_session(db)

        # DEFAULT_WEIGHTS でスコア計算
        compute_scores_for_session(db, 215)
        default_scores = {s.member_id: s.total for s in db.query(MemberScore).all()}

        # 重み変更: transparency を大幅に引き上げ
        db.add(
            WeightVersion(
                version="v_test",
                legislative_activity=0.10,
                voting_behavior=0.10,
                policy_influence=0.10,
                transparency=0.50,
                question_quality=0.20,
                reason="E2Eテスト: 重み変更の影響確認",
                is_active=True,
            )
        )
        db.commit()

        # 既存スコアを削除して再計算
        db.query(MemberScore).delete()
        db.query(ScoreAuditLog).delete()
        db.commit()

        compute_scores_for_session(db, 215)
        new_scores = {s.member_id: s.total for s in db.query(MemberScore).all()}

        # 少なくとも一部の議員でスコアが変わっているはず
        changed = sum(
            1 for mid in default_scores if abs(default_scores[mid] - new_scores[mid]) > 0.5
        )
        assert changed > 0, "重みを大幅に変更したのにスコアが変わらない → DB重みが使われていない"

    def test_weights_version_recorded_in_audit(self, db):
        """監査ログにweights_versionが記録されること。"""
        _seed_full_session(db)
        db.add(
            WeightVersion(
                version="v2.0_test",
                legislative_activity=0.25,
                voting_behavior=0.20,
                policy_influence=0.20,
                transparency=0.15,
                question_quality=0.20,
                reason="バージョン記録テスト",
                is_active=True,
            )
        )
        db.commit()

        compute_scores_for_session(db, 215)

        audits = db.query(ScoreAuditLog).all()
        assert len(audits) > 0
        for a in audits:
            assert a.weights_version == "v2.0_test", (
                f"weights_version={a.weights_version} が期待値と異なる"
            )

    def test_no_active_version_uses_defaults(self, db):
        """アクティブなWeightVersionがない場合DEFAULT_WEIGHTSが使われること。"""
        _seed_full_session(db)

        # WeightVersionは空
        assert db.query(WeightVersion).count() == 0

        compute_scores_for_session(db, 215)
        scores = db.query(MemberScore).all()
        assert len(scores) > 0

        # 監査ログのweights_versionはNone
        for a in db.query(ScoreAuditLog).all():
            assert a.weights_version is None


# =====================================================================
# 5. 設計思想不変量（数学的保証）
# =====================================================================


class TestDesignInvariants:
    """どんな入力・実装変更でも必ず成立すべき不変量。"""

    def test_normalization_preserves_ordering(self, db):
        """raw scoreの大小関係が同一グループ内の正規化後も保存されること。

        正規化はchamber × role_categoryグループ内で行われるため、
        グループ内での順序保存のみを検証する。
        """
        _seed_full_session(db)
        compute_scores_for_session(db, 215)

        scores = db.query(MemberScore).all()
        members = {m.id: m for m in db.query(Member).all()}

        # グループ分け
        groups: dict[tuple, list[MemberScore]] = {}
        for s in scores:
            m = members[s.member_id]
            key = (m.chamber, m.role_category or "unknown")
            groups.setdefault(key, []).append(s)

        for group_key, group_scores in groups.items():
            raw_pairs = [(s.member_id, s.legislative_activity_raw) for s in group_scores]
            norm_map = {s.member_id: s.legislative_activity for s in group_scores}

            raw_pairs.sort(key=lambda x: x[1])
            for i in range(len(raw_pairs) - 1):
                mid_a = raw_pairs[i][0]
                mid_b = raw_pairs[i + 1][0]
                raw_a = raw_pairs[i][1]
                raw_b = raw_pairs[i + 1][1]
                if raw_a < raw_b:
                    assert norm_map[mid_a] <= norm_map[mid_b], (
                        f"group={group_key}: "
                        f"raw {raw_a} < {raw_b} なのに "
                        f"norm {norm_map[mid_a]} > {norm_map[mid_b]} "
                        "→ 正規化が順序を破壊"
                    )

    def test_score_deterministic(self, db):
        """同じ入力で2回計算しても同じ結果になること。"""
        _seed_full_session(db)

        compute_scores_for_session(db, 215)
        first = {s.member_id: s.total for s in db.query(MemberScore).all()}

        # 同じデータで再計算
        compute_scores_for_session(db, 215)
        second = {s.member_id: s.total for s in db.query(MemberScore).all()}

        for mid in first:
            assert first[mid] == second[mid], (
                f"member_id={mid}: 1回目={first[mid]}, 2回目={second[mid]} → スコアリングが非決定的"
            )

    def test_no_axis_ignored_in_total(self, db):
        """5軸全てが総合スコアに影響すること（重み0の軸がないこと）。"""
        session = DietSession(id=1, session_number=215, kind="通常")
        db.add(session)

        # 2人の議員: 1つの軸だけ異なる
        for i in [1, 2]:
            db.add(
                Member(
                    id=i,
                    name=f"テスト{i}",
                    chamber="representatives",
                    party="無所属",
                    role_category="member",
                )
            )
        db.commit()

        # 直接MemberScoreを作って検証
        from app.services.scoring import compute_total

        base = {k: 50.0 for k in DEFAULT_WEIGHTS}
        base_total = compute_total(base)

        for axis in DEFAULT_WEIGHTS:
            modified = dict(base)
            modified[axis] = 80.0
            modified_total = compute_total(modified)
            assert modified_total > base_total, (
                f"{axis}を50→80にしてもtotalが変わらない → この軸の重みが0"
            )

    def test_weights_always_sum_to_one_at_runtime(self, db):
        """実行時のDEFAULT_WEIGHTSが常に合計1.0であること。"""
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-10, (
            f"DEFAULT_WEIGHTSの合計={total} ≠ 1.0 → スコアの最大値が100にならない"
        )


# =====================================================================
# 6. レビューAPI E2E
# =====================================================================


class TestReviewAPIE2E:
    """レビューシステムの全フローをAPIレベルで検証。"""

    def _setup_member(self, db):
        db.add(DietSession(id=1, session_number=215, kind="通常"))
        db.add(
            Member(
                id=1,
                name="レビュー対象議員",
                chamber="representatives",
                party="テスト党",
            )
        )
        db.commit()

    def test_create_review(self, client, db):
        """レビュー作成→取得の全フロー。"""
        self._setup_member(db)

        resp = client.post(
            "/api/v1/members/1/reviews",
            json={
                "reviewer_id": "test-uuid-001",
                "display_name": "テストユーザー",
                "legislative_activity": 80,
                "voting_behavior": 70,
                "policy_influence": 60,
                "transparency": 50,
                "question_quality": 90,
                "comment": "良い議員だと思います",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == (80 + 70 + 60 + 50 + 90) / 5
        assert data["comment"] == "良い議員だと思います"

    def test_upsert_same_reviewer(self, client, db):
        """同じreviewer_idで2回POSTするとupdateになること。"""
        self._setup_member(db)
        reviewer_id = "test-uuid-002"

        # 1回目
        client.post(
            "/api/v1/members/1/reviews",
            json={
                "reviewer_id": reviewer_id,
                "legislative_activity": 50,
                "voting_behavior": 50,
                "policy_influence": 50,
                "transparency": 50,
                "question_quality": 50,
            },
        )

        # 2回目（更新）
        resp = client.post(
            "/api/v1/members/1/reviews",
            json={
                "reviewer_id": reviewer_id,
                "legislative_activity": 90,
                "voting_behavior": 90,
                "policy_influence": 90,
                "transparency": 90,
                "question_quality": 90,
                "comment": "更新しました",
            },
        )
        assert resp.status_code == 200

        # 1件しかないこと
        list_resp = client.get("/api/v1/members/1/reviews")
        assert list_resp.json()["total"] == 1
        assert list_resp.json()["items"][0]["comment"] == "更新しました"

    def test_review_summary_calculation(self, client, db):
        """複数レビューのサマリーが正しく計算されること。"""
        self._setup_member(db)

        # 2人のレビュアーが異なるスコアを付ける
        for i, scores in enumerate([(80, 70, 60, 50, 90), (40, 50, 60, 70, 30)]):
            client.post(
                "/api/v1/members/1/reviews",
                json={
                    "reviewer_id": f"reviewer-{i}",
                    "legislative_activity": scores[0],
                    "voting_behavior": scores[1],
                    "policy_influence": scores[2],
                    "transparency": scores[3],
                    "question_quality": scores[4],
                },
            )

        resp = client.get("/api/v1/members/1/review-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_count"] == 2
        assert data["average_legislative_activity"] == 60.0  # (80+40)/2
        assert data["average_voting_behavior"] == 60.0  # (70+50)/2
        assert data["average_question_quality"] == 60.0  # (90+30)/2

    def test_like_toggle(self, client, db):
        """いいねのトグル動作。"""
        self._setup_member(db)

        # レビュー作成
        create_resp = client.post(
            "/api/v1/members/1/reviews",
            json={
                "reviewer_id": "author-001",
                "legislative_activity": 50,
                "voting_behavior": 50,
                "policy_influence": 50,
                "transparency": 50,
                "question_quality": 50,
            },
        )
        review_id = create_resp.json()["id"]

        # いいね追加
        like_resp = client.post(
            f"/api/v1/reviews/{review_id}/like",
            json={"liker_id": "liker-001"},
        )
        assert like_resp.json()["like_count"] == 1
        assert like_resp.json()["is_liked"] is True

        # いいね解除（トグル）
        unlike_resp = client.post(
            f"/api/v1/reviews/{review_id}/like",
            json={"liker_id": "liker-001"},
        )
        assert unlike_resp.json()["like_count"] == 0
        assert unlike_resp.json()["is_liked"] is False

    def test_delete_review_auth(self, client, db):
        """他人のレビューは削除できないこと。"""
        self._setup_member(db)

        create_resp = client.post(
            "/api/v1/members/1/reviews",
            json={
                "reviewer_id": "author-001",
                "legislative_activity": 50,
                "voting_behavior": 50,
                "policy_influence": 50,
                "transparency": 50,
                "question_quality": 50,
            },
        )
        review_id = create_resp.json()["id"]

        # 別のユーザーが削除しようとする
        del_resp = client.delete(f"/api/v1/reviews/{review_id}?reviewer_id=attacker-999")
        assert del_resp.status_code == 403

        # 正しいユーザーなら削除できる
        del_resp = client.delete(f"/api/v1/reviews/{review_id}?reviewer_id=author-001")
        assert del_resp.status_code == 200

    def test_review_score_validation(self, client, db):
        """スコアが0-100の範囲外ならバリデーションエラーになること。"""
        self._setup_member(db)

        resp = client.post(
            "/api/v1/members/1/reviews",
            json={
                "reviewer_id": "test-001",
                "legislative_activity": 150,  # 範囲外
                "voting_behavior": 50,
                "policy_influence": 50,
                "transparency": 50,
                "question_quality": 50,
            },
        )
        assert resp.status_code == 422, "0-100範囲外のスコアが受け入れられてしまった"

    def test_review_sort_by_likes(self, client, db):
        """いいね順ソートが正しく機能すること。"""
        self._setup_member(db)

        # 3件のレビュー
        ids = []
        for i in range(3):
            resp = client.post(
                "/api/v1/members/1/reviews",
                json={
                    "reviewer_id": f"reviewer-{i}",
                    "legislative_activity": 50,
                    "voting_behavior": 50,
                    "policy_influence": 50,
                    "transparency": 50,
                    "question_quality": 50,
                    "comment": f"レビュー{i}",
                },
            )
            ids.append(resp.json()["id"])

        # 2番目のレビューに2いいね、3番目に1いいね
        for liker in ["liker-a", "liker-b"]:
            client.post(
                f"/api/v1/reviews/{ids[1]}/like",
                json={"liker_id": liker},
            )
        client.post(
            f"/api/v1/reviews/{ids[2]}/like",
            json={"liker_id": "liker-c"},
        )

        # いいね順で取得
        resp = client.get("/api/v1/members/1/reviews?sort=likes")
        items = resp.json()["items"]
        assert items[0]["like_count"] >= items[1]["like_count"], "いいね順ソートが機能していない"
