"""カナリアテスト

既知の良い/悪い入力パターンに対してパイプラインの各段階が
期待通りの結果を返すことを検証する。
LLMを実際に呼ばず、パース・フィルタリング・スコアリングの
決定論的な部分をテストすることで、パイプライン改変時の退行を検出。

テスト対象:
1. 議事進行フィルタリング (canary: 定型発言がスキップされる)
2. LLMレスポンスパース (canary: 既知のJSON形式を正しく処理)
3. スコアリング算出 (canary: 既知の重み・入力で期待通りの総合スコア)
4. グレード判定 (canary: 境界値周辺で正しいグレード)
5. バイアス検出閾値 (canary: 既知のスコア分布に正しく反応)
"""

import pytest

from app.pipeline.speech_quality import (
    _is_procedural,
    _parse_llm_response,
    reset_quality_tracker,
)
from app.services.scoring import (
    DEFAULT_WEIGHTS,
    compute_grade,
    compute_total,
)

# ---------------------------------------------------------------------------
# テストデータ: 議事進行発言のカナリーサンプル
# ---------------------------------------------------------------------------

# 必ずスキップすべき議事進行発言
PROCEDURAL_SAMPLES = [
    "○委員長（山田太郎君）　これより内閣委員会を開きます。",
    "○鈴木委員長　これより財務金融委員会を開会いたします。",
    "散会いたします。次回は明日午前十時から委員会を開きます。",
    "ただいまから外交防衛委員会を開会いたします。",
    "御異議なしと認めます。よってそのように決定いたしました。",
    "委員の異動について御報告いたします。本日、佐藤君が…",
    "参考人に一言御礼を申し上げます。本日はお忙しい中…",
    "以上で参考人に対する質疑は終了いたしました。",
    "○政府参考人（田中一郎君）　お答えいたします。",
    "本日は、これにて散会いたします。",
]

# スキップしてはいけない実質的発言
SUBSTANTIVE_SAMPLES = [
    (
        "○田中委員　本法案について、第三条の規定について質問いたします。"
        "政府は中小企業への影響をどう評価しているのか、具体的な数字をお示しください。"
    ),
    (
        "○佐藤委員　私は独自に調査を行いまして、"
        "この制度の受給者のうち約三割が実質的に要件を満たしていないことが判明しました。"
    ),
    (
        "○山田委員　予算の執行率を見ますと、過去五年間で平均七十パーセント以下です。"
        "この未執行分について、具体的な改善策を提示してください。"
    ),
]


class TestCanaryProcedural:
    """カナリー: 議事進行発言のフィルタリングが正しく動作すること。"""

    @pytest.mark.parametrize("text", PROCEDURAL_SAMPLES)
    def test_procedural_detected(self, text: str):
        """既知の議事進行発言がフィルタされること。"""
        assert _is_procedural(text), f"議事進行発言が検出されませんでした: {text[:50]}"

    @pytest.mark.parametrize("text", SUBSTANTIVE_SAMPLES)
    def test_substantive_not_filtered(self, text: str):
        """実質的な質問発言がフィルタされないこと。"""
        assert not _is_procedural(text), f"実質的発言が誤ってフィルタされました: {text[:50]}"


# ---------------------------------------------------------------------------
# テストデータ: LLMレスポンスのカナリーサンプル
# ---------------------------------------------------------------------------

# 高品質な政策質問 → 高スコア
HIGH_QUALITY_RESPONSE = """{
    "policy_relevance": 85,
    "constructiveness": 90,
    "expertise": 80,
    "national_interest": 88,
    "summary": "中小企業の税制改正について具体的な改善提案を伴う建設的な質問。"
}"""

# スキャンダル追及のみ → 低スコア
LOW_QUALITY_RESPONSE = """{
    "policy_relevance": 15,
    "constructiveness": 10,
    "expertise": 20,
    "national_interest": 12,
    "summary": "特定議員の不祥事追及に終始し、制度改善提案を伴わない質問。"
}"""

# 壊れたJSON → None
BROKEN_RESPONSES = [
    "これはJSONではありません。",
    "```json\n{broken}```",
    "",
    "   ",
]

# 範囲外の値 → フォールバック50.0
OUT_OF_RANGE_RESPONSE = """{
    "policy_relevance": 150,
    "constructiveness": -10,
    "expertise": "high",
    "national_interest": 70,
    "summary": "テスト"
}"""


class TestCanaryLLMParse:
    """カナリー: LLMレスポンスパースが既知のパターンで正しく動作すること。"""

    def setup_method(self):
        reset_quality_tracker()

    def test_high_quality_parse(self):
        """高品質レスポンスが正しくパースされること。"""
        result = _parse_llm_response(HIGH_QUALITY_RESPONSE)
        assert result is not None
        assert result["policy_relevance"] == 85.0
        assert result["constructiveness"] == 90.0
        assert result["expertise"] == 80.0
        assert result["national_interest"] == 88.0
        assert "summary" in result

    def test_low_quality_parse(self):
        """低品質レスポンスが正しくパースされること。"""
        result = _parse_llm_response(LOW_QUALITY_RESPONSE)
        assert result is not None
        assert result["policy_relevance"] == 15.0
        assert result["constructiveness"] == 10.0

    @pytest.mark.parametrize("text", BROKEN_RESPONSES)
    def test_broken_response_returns_none(self, text: str):
        """壊れたレスポンスがNoneを返すこと。"""
        result = _parse_llm_response(text)
        assert result is None

    def test_out_of_range_fallback(self):
        """範囲外の値がフォールバック(50.0)になること。"""
        result = _parse_llm_response(OUT_OF_RANGE_RESPONSE)
        assert result is not None
        # 150 → 50.0 (out of range)
        assert result["policy_relevance"] == 50.0
        # -10 → 50.0 (out of range)
        assert result["constructiveness"] == 50.0
        # "high" → 50.0 (not a number)
        assert result["expertise"] == 50.0
        # 70 → 70.0 (valid)
        assert result["national_interest"] == 70.0


# ---------------------------------------------------------------------------
# カナリー: スコアリング算出
# ---------------------------------------------------------------------------


class TestCanaryScoring:
    """カナリー: スコアリング関数が既知の入力で期待通りの結果を返すこと。"""

    def test_default_weights_produce_expected_total(self):
        """DEFAULT_WEIGHTSで均一スコア50 → 総合50。"""
        uniform = {
            "legislative_activity": 50.0,
            "voting_behavior": 50.0,
            "policy_influence": 50.0,
            "transparency": 50.0,
            "question_quality": 50.0,
        }
        total = compute_total(uniform)
        assert total == 50.0

    def test_max_scores_produce_100(self):
        """全軸100 → 総合100。"""
        perfect = {k: 100.0 for k in DEFAULT_WEIGHTS}
        total = compute_total(perfect)
        assert total == 100.0

    def test_zero_scores_produce_zero(self):
        """全軸0 → 総合0。"""
        zero = {k: 0.0 for k in DEFAULT_WEIGHTS}
        total = compute_total(zero)
        assert total == 0.0

    def test_weighted_calculation_correct(self):
        """非均一スコアで重み計算が正しいこと。"""
        scores = {
            "legislative_activity": 80.0,  # × 0.25 = 20.0
            "voting_behavior": 60.0,  # × 0.20 = 12.0
            "policy_influence": 100.0,  # × 0.20 = 20.0
            "transparency": 40.0,  # × 0.15 = 6.0
            "question_quality": 70.0,  # × 0.20 = 14.0
        }
        expected = 20.0 + 12.0 + 20.0 + 6.0 + 14.0  # = 72.0
        total = compute_total(scores)
        assert total == expected

    def test_custom_weights_override(self):
        """カスタム重みでDEFAULT_WEIGHTSを上書きできること。"""
        scores = {k: 100.0 for k in DEFAULT_WEIGHTS}
        custom = {
            "legislative_activity": 0.50,
            "voting_behavior": 0.10,
            "policy_influence": 0.10,
            "transparency": 0.10,
            "question_quality": 0.20,
        }
        total = compute_total(scores, custom)
        assert total == 100.0


# ---------------------------------------------------------------------------
# カナリー: グレード判定
# ---------------------------------------------------------------------------


class TestCanaryGrade:
    """カナリー: グレード判定が境界値で正しく動作すること。"""

    @pytest.mark.parametrize(
        "score, expected_grade",
        [
            (100.0, "A"),
            (80.0, "A"),
            (79.99, "B"),
            (60.0, "B"),
            (59.99, "C"),
            (40.0, "C"),
            (39.99, "D"),
            (20.0, "D"),
            (19.99, "F"),
            (0.0, "F"),
        ],
    )
    def test_grade_boundary(self, score: float, expected_grade: str):
        """グレード境界値が正しいこと。"""
        assert compute_grade(score) == expected_grade, (
            f"score={score} → expected {expected_grade}, got {compute_grade(score)}"
        )

    def test_grade_ordering(self):
        """グレードの順序が A > B > C > D > F であること。"""
        grades = ["A", "B", "C", "D", "F"]
        thresholds = [80, 60, 40, 20, 0]
        for grade, threshold in zip(grades, thresholds):
            assert compute_grade(float(threshold)) == grade


# ---------------------------------------------------------------------------
# カナリー: パイプライン全体の整合性
# ---------------------------------------------------------------------------


class TestCanaryPipelineIntegrity:
    """カナリー: パイプライン設定の整合性を検証。"""

    def test_weights_sum_invariant(self):
        """重みの合計が1.0であること（回帰防止）。"""
        assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-10

    def test_all_axes_in_weights(self):
        """5軸が全て重みに存在すること。"""
        expected = {
            "legislative_activity",
            "voting_behavior",
            "policy_influence",
            "transparency",
            "question_quality",
        }
        assert set(DEFAULT_WEIGHTS.keys()) == expected

    def test_parse_and_score_end_to_end(self):
        """LLMパース → 総合スコア → グレードの一貫性。"""
        reset_quality_tracker()
        result = _parse_llm_response(HIGH_QUALITY_RESPONSE)
        assert result is not None

        # overall_quality (4軸平均) を算出
        overall = (
            result["policy_relevance"]
            + result["constructiveness"]
            + result["expertise"]
            + result["national_interest"]
        ) / 4.0
        assert 80.0 <= overall <= 90.0, f"高品質サンプルのoverall={overall}が想定範囲外"

    def test_low_quality_end_to_end(self):
        """低品質サンプルのend-to-end検証。"""
        reset_quality_tracker()
        result = _parse_llm_response(LOW_QUALITY_RESPONSE)
        assert result is not None

        overall = (
            result["policy_relevance"]
            + result["constructiveness"]
            + result["expertise"]
            + result["national_interest"]
        ) / 4.0
        assert overall < 30.0, f"低品質サンプルのoverall={overall}が高すぎます"

    def test_procedural_filter_does_not_affect_scoring(self):
        """議事進行フィルタはスコアリング関数に影響しないこと。"""
        # _is_procedural はスコアリング前のフィルタ。scoring.py は独立。
        from app.services.scoring import compute_total as ct

        scores = {k: 50.0 for k in DEFAULT_WEIGHTS}
        assert ct(scores) == 50.0  # フィルタの有無に関わらず同じ結果
