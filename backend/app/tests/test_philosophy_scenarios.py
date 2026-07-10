"""設計思想シナリオテスト

CLAUDE.mdの設計思想が実際のスコアリングロジックで正しく機能するかを
具体的なシナリオで検証する。
"""

from app.pipeline.speech_quality import _is_procedural, _parse_llm_response
from app.services.scoring import (
    _normalize_group,
    compute_grade,
    compute_total,
)

# ---------------------------------------------------------------------------
# シナリオ1: スキャンダル追及のみの質問 → 低品質
# ---------------------------------------------------------------------------


class TestScenarioScandal:
    """スキャンダル追及のみ（制度改善提案なし）の質問は低品質判定されるべき。"""

    def test_scandal_only_should_score_low_on_constructiveness(self):
        """スキャンダル追及のみのLLM応答は constructiveness が低いこと。

        LLMが正しく評価した場合、constructiveness は低くなるべき。
        ここではパースロジックが低スコアを正しく受け入れることを検証。
        """
        response = (
            '{"policy_relevance": 15, "constructiveness": 5, '
            '"expertise": 20, "national_interest": 10, '
            '"summary": "スキャンダル追及のみ"}'
        )
        result = _parse_llm_response(response)
        assert result is not None
        assert result["constructiveness"] == 5.0
        assert result["policy_relevance"] == 15.0
        # 全軸の平均 = (15 + 5 + 20 + 10) / 4 = 12.5 → 低品質
        avg = (
            result["policy_relevance"]
            + result["constructiveness"]
            + result["expertise"]
            + result["national_interest"]
        ) / 4
        assert avg < 30, "スキャンダル追及のみの質問は平均30未満であるべき"

    def test_scandal_with_reform_proposal_scores_higher(self):
        """スキャンダルでも制度改善提案を伴う場合は中〜高評価であるべき。"""
        response = (
            '{"policy_relevance": 70, "constructiveness": 65, '
            '"expertise": 50, "national_interest": 60, '
            '"summary": "裏金問題を踏まえた政治資金規正法改正案を提案"}'
        )
        result = _parse_llm_response(response)
        assert result is not None
        avg = (
            result["policy_relevance"]
            + result["constructiveness"]
            + result["expertise"]
            + result["national_interest"]
        ) / 4
        assert avg >= 50, "制度改善を伴うスキャンダル追及は50以上であるべき"


# ---------------------------------------------------------------------------
# シナリオ2: 高品質な政策議論 → 高品質
# ---------------------------------------------------------------------------


class TestScenarioPolicyDebate:
    """具体的な政策提案を伴う質問は高品質と判定されるべき。"""

    def test_concrete_policy_proposal_scores_high(self):
        """独自データ＋具体的改善案のLLM応答は高スコア。"""
        response = (
            '{"policy_relevance": 90, "constructiveness": 85, '
            '"expertise": 80, "national_interest": 85, '
            '"summary": "独自調査データに基づく社会保障改革案"}'
        )
        result = _parse_llm_response(response)
        assert result is not None
        avg = (
            result["policy_relevance"]
            + result["constructiveness"]
            + result["expertise"]
            + result["national_interest"]
        ) / 4
        assert avg >= 80, "高品質な政策議論は平均80以上であるべき"

    def test_public_info_only_question_scores_low(self):
        """公開情報の確認だけの質問は低評価。"""
        response = (
            '{"policy_relevance": 20, "constructiveness": 10, '
            '"expertise": 5, "national_interest": 25, '
            '"summary": "政府公表資料の内容を聞いただけ"}'
        )
        result = _parse_llm_response(response)
        assert result is not None
        avg = (
            result["policy_relevance"]
            + result["constructiveness"]
            + result["expertise"]
            + result["national_interest"]
        ) / 4
        assert avg < 30, "公開情報の確認質問は平均30未満であるべき"


# ---------------------------------------------------------------------------
# シナリオ3: 与野党の公平性
# ---------------------------------------------------------------------------


class TestScenarioPartyFairness:
    """与党・野党の立場によるスコア差が生じない仕組みを検証。"""

    def test_normalization_groups_by_chamber_and_role(self):
        """パーセンタイル正規化が chamber × role_category 内で行われること。

        これにより同条件の議員同士で比較される。
        """
        # 衆議院・一般議員グループ
        raw_scores = {
            1: {
                "legislative_activity": 10,
                "voting_behavior": 50,
                "policy_influence": 30,
                "transparency": 20,
                "question_quality": 40,
            },
            2: {
                "legislative_activity": 30,
                "voting_behavior": 70,
                "policy_influence": 50,
                "transparency": 40,
                "question_quality": 60,
            },
            3: {
                "legislative_activity": 50,
                "voting_behavior": 90,
                "policy_influence": 70,
                "transparency": 60,
                "question_quality": 80,
            },
        }

        # グループ内で正規化
        normalized = {}
        _normalize_group(raw_scores, [1, 2, 3], normalized)

        # 最低と最高がそれぞれ0と100に近い
        assert normalized[1]["legislative_activity"] == 0.0
        assert normalized[3]["legislative_activity"] == 100.0
        # 中間はちょうど50
        assert normalized[2]["legislative_activity"] == 50.0

    def test_ruling_and_opposition_get_same_treatment(self):
        """同じ raw score を持つ議員は、政党に関係なく同じ正規化スコアを得ること。"""
        # 全員同じスコア → 全員50.0
        raw_scores = {
            1: {
                "legislative_activity": 30,
                "voting_behavior": 30,
                "policy_influence": 30,
                "transparency": 30,
                "question_quality": 30,
            },
            2: {
                "legislative_activity": 30,
                "voting_behavior": 30,
                "policy_influence": 30,
                "transparency": 30,
                "question_quality": 30,
            },
        }
        normalized = {}
        _normalize_group(raw_scores, [1, 2], normalized)

        assert normalized[1]["legislative_activity"] == normalized[2]["legislative_activity"]
        assert normalized[1]["voting_behavior"] == normalized[2]["voting_behavior"]


# ---------------------------------------------------------------------------
# シナリオ4: 能力と品性の独立性
# ---------------------------------------------------------------------------


class TestScenarioAbilityIndependence:
    """能力の高い政治家は個人的問題があってもスコアが高くなるべき。"""

    def test_high_ability_gets_high_grade(self):
        """全軸高スコアの議員はグレードAであること。"""
        normalized = {
            "legislative_activity": 90,
            "voting_behavior": 85,
            "policy_influence": 80,
            "transparency": 75,
            "question_quality": 88,
        }
        total = compute_total(normalized)
        grade = compute_grade(total)
        assert grade == "A"
        assert total >= 80

    def test_low_ability_gets_low_grade_despite_no_scandal(self):
        """問題を起こさないだけで能力が低い議員はスコアが低いこと。"""
        normalized = {
            "legislative_activity": 5,
            "voting_behavior": 10,
            "policy_influence": 0,
            "transparency": 5,
            "question_quality": 8,
        }
        total = compute_total(normalized)
        grade = compute_grade(total)
        assert grade == "F"
        assert total < 20


# ---------------------------------------------------------------------------
# シナリオ5: 議事進行発言のフィルタリング
# ---------------------------------------------------------------------------


class TestScenarioProceduralFiltering:
    """議事進行・手続き的な発言はスコアリング対象外であること。"""

    def test_chair_opening_is_procedural(self):
        assert _is_procedural("○委員長（山田太郎君）　これより会議を開きます。")

    def test_session_close_is_procedural(self):
        assert _is_procedural("本日は、これにて散会いたします。")

    def test_expert_testimony_greeting_is_procedural(self):
        assert _is_procedural("参考人の方々に一言御礼を申し上げます。")

    def test_substantive_question_is_not_procedural(self):
        """実質的な質問は議事進行と判定されないこと。"""
        assert not _is_procedural(
            "総理、今回の社会保障制度改革について、"
            "具体的にどのような予算措置を講じるおつもりか、お聞かせください。"
        )

    def test_government_reference_is_procedural(self):
        assert _is_procedural("○政府参考人（鈴木一郎君）　お答え申し上げます。")


# ---------------------------------------------------------------------------
# シナリオ6: LLMフォールバックの安全性
# ---------------------------------------------------------------------------


class TestScenarioLLMFallback:
    """LLMが不正な値を返した場合のフォールバック動作を検証。"""

    def test_invalid_json_returns_none(self):
        """JSON以外の文字列はNoneを返す。"""
        assert _parse_llm_response("This is not JSON") is None

    def test_out_of_range_scores_fallback_to_50(self):
        """0-100範囲外のスコアは50.0にフォールバック。"""
        response = (
            '{"policy_relevance": 150, "constructiveness": -10, '
            '"expertise": 50, "national_interest": 70}'
        )
        result = _parse_llm_response(response)
        assert result is not None
        assert result["policy_relevance"] == 50.0  # 150 → 50
        assert result["constructiveness"] == 50.0  # -10 → 50
        assert result["expertise"] == 50.0  # 正常値
        assert result["national_interest"] == 70.0  # 正常値

    def test_missing_keys_fallback_to_50(self):
        """必須キーが欠落した場合は50.0にフォールバック。"""
        response = '{"policy_relevance": 80}'
        result = _parse_llm_response(response)
        assert result is not None
        assert result["policy_relevance"] == 80.0
        assert result["constructiveness"] == 50.0
        assert result["expertise"] == 50.0
        assert result["national_interest"] == 50.0

    def test_string_values_fallback_to_50(self):
        """文字列値は50.0にフォールバック。"""
        response = (
            '{"policy_relevance": "high", "constructiveness": 60, '
            '"expertise": null, "national_interest": 70}'
        )
        result = _parse_llm_response(response)
        assert result is not None
        assert result["policy_relevance"] == 50.0  # "high" → 50
        assert result["constructiveness"] == 60.0  # 正常
        assert result["expertise"] == 50.0  # null → 50
        assert result["national_interest"] == 70.0  # 正常
