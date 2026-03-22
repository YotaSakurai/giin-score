"""スコアリングエンジンの単体テスト"""

import pytest

from app.services.scoring import (
    DEFAULT_WEIGHTS,
    _bill_kind_weight,
    _normalize_group,
    _sponsor_weight,
    compute_grade,
    compute_total,
)


class TestSponsorWeight:
    def test_primary_sponsor(self):
        assert _sponsor_weight("primary", 1) == 1.0
        assert _sponsor_weight("primary", 100) == 1.0

    def test_co_sponsor_small_group(self):
        assert _sponsor_weight("co-sponsor", 3) == 0.5
        assert _sponsor_weight("co-sponsor", 5) == 0.5

    def test_co_sponsor_medium_group(self):
        assert _sponsor_weight("co-sponsor", 6) == 0.3
        assert _sponsor_weight("co-sponsor", 20) == 0.3

    def test_co_sponsor_large_group(self):
        assert _sponsor_weight("co-sponsor", 21) == 0.1
        assert _sponsor_weight("co-sponsor", 100) == 0.1


class TestBillKindWeight:
    def test_new_legislation_kakuhou(self):
        # 閣法: base=1.0, 改正なし -> 1.0
        assert _bill_kind_weight("民法", "閣法") == 1.0
        assert _bill_kind_weight("国民投票法", "閣法") == 1.0

    def test_new_legislation_shuhou(self):
        # 衆法: base=0.8, 改正なし -> 0.8
        assert _bill_kind_weight("民法", "衆法") == 0.8
        assert _bill_kind_weight("国民投票法", "参法") == 0.8

    def test_minor_amendment_kakuhou(self):
        # 閣法: base=1.0, 軽微改正 -> 1.0 * 0.3 = 0.3
        assert _bill_kind_weight("民法の一部改正", "閣法") == 0.3
        assert _bill_kind_weight("関係法律の整備等に関する法律の一部改正", "閣法") == 0.3

    def test_minor_amendment_shuhou(self):
        # 衆法: base=0.8, 軽微改正 -> 0.8 * 0.3 = 0.24
        assert _bill_kind_weight("民法の一部改正", "衆法") == pytest.approx(0.24)

    def test_major_amendment_kakuhou(self):
        # 閣法: base=1.0, 大規模改正 -> 1.0 * 0.7 = 0.7
        assert _bill_kind_weight("刑法改正に関する法律", "閣法") == 0.7

    def test_major_amendment_shuhou(self):
        # 衆法: base=0.8, 大規模改正 -> 0.8 * 0.7 = 0.56
        assert _bill_kind_weight("刑法改正に関する法律", "衆法") == pytest.approx(0.56)


class TestComputeTotal:
    def test_default_weights(self):
        normalized = {
            "legislative_activity": 80.0,
            "voting_behavior": 60.0,
            "policy_influence": 40.0,
            "transparency": 20.0,
            "question_quality": 50.0,
        }
        # 80*0.25 + 60*0.20 + 40*0.20 + 20*0.15 + 50*0.20 = 20+12+8+3+10 = 53.0
        assert compute_total(normalized) == 53.0

    def test_custom_weights(self):
        normalized = {
            "legislative_activity": 100.0,
            "voting_behavior": 100.0,
            "policy_influence": 100.0,
            "transparency": 100.0,
            "question_quality": 100.0,
        }
        custom_weights = {
            "legislative_activity": 0.20,
            "voting_behavior": 0.20,
            "policy_influence": 0.20,
            "transparency": 0.20,
            "question_quality": 0.20,
        }
        assert compute_total(normalized, custom_weights) == 100.0

    def test_all_zeros(self):
        normalized = {
            "legislative_activity": 0.0,
            "voting_behavior": 0.0,
            "policy_influence": 0.0,
            "transparency": 0.0,
            "question_quality": 0.0,
        }
        assert compute_total(normalized) == 0.0

    def test_missing_keys_default_to_zero(self):
        normalized = {"legislative_activity": 100.0}
        assert compute_total(normalized) == 25.0


class TestComputeGrade:
    def test_grade_a(self):
        assert compute_grade(100.0) == "A"
        assert compute_grade(80.0) == "A"

    def test_grade_b(self):
        assert compute_grade(79.9) == "B"
        assert compute_grade(60.0) == "B"

    def test_grade_c(self):
        assert compute_grade(59.9) == "C"
        assert compute_grade(40.0) == "C"

    def test_grade_d(self):
        assert compute_grade(39.9) == "D"
        assert compute_grade(20.0) == "D"

    def test_grade_f(self):
        assert compute_grade(19.9) == "F"
        assert compute_grade(0.0) == "F"


class TestNormalization:
    def test_percentile_rank_basic(self):
        raw_scores = {
            1: {
                "legislative_activity": 10,
                "voting_behavior": 50,
                "policy_influence": 30,
                "transparency": 20,
                "question_quality": 10,
            },
            2: {
                "legislative_activity": 20,
                "voting_behavior": 40,
                "policy_influence": 60,
                "transparency": 40,
                "question_quality": 20,
            },
            3: {
                "legislative_activity": 30,
                "voting_behavior": 30,
                "policy_influence": 90,
                "transparency": 60,
                "question_quality": 30,
            },
            4: {
                "legislative_activity": 40,
                "voting_behavior": 20,
                "policy_influence": 20,
                "transparency": 80,
                "question_quality": 40,
            },
            5: {
                "legislative_activity": 50,
                "voting_behavior": 10,
                "policy_influence": 10,
                "transparency": 100,
                "question_quality": 50,
            },
        }
        member_ids = [1, 2, 3, 4, 5]
        normalized = {}
        _normalize_group(raw_scores, member_ids, normalized)

        # member 1 has lowest LAS (rank 0/(5-1) = 0.0)
        assert normalized[1]["legislative_activity"] == 0.0
        # member 5 has highest LAS (rank 4/(5-1) = 100.0)
        assert normalized[5]["legislative_activity"] == 100.0
        # member 3 has middle LAS (rank 2/(5-1) = 50.0)
        assert normalized[3]["legislative_activity"] == 50.0

    def test_single_member_group(self):
        raw_scores = {
            1: {
                "legislative_activity": 50,
                "voting_behavior": 50,
                "policy_influence": 50,
                "transparency": 50,
                "question_quality": 50,
            },
        }
        normalized = {}
        _normalize_group(raw_scores, [1], normalized)
        # Single member -> 50.0 percentile
        assert normalized[1]["legislative_activity"] == 50.0

    def test_tied_scores(self):
        raw_scores = {
            1: {
                "legislative_activity": 10,
                "voting_behavior": 10,
                "policy_influence": 10,
                "transparency": 10,
                "question_quality": 10,
            },
            2: {
                "legislative_activity": 10,
                "voting_behavior": 10,
                "policy_influence": 10,
                "transparency": 10,
                "question_quality": 10,
            },
        }
        normalized = {}
        _normalize_group(raw_scores, [1, 2], normalized)
        # Both exist in normalized and have the same percentile (average rank)
        assert 1 in normalized
        assert 2 in normalized
        # avg_rank = (0+1)/2 = 0.5, percentile = 0.5/(2-1)*100 = 50.0
        assert normalized[1]["legislative_activity"] == 50.0
        assert normalized[2]["legislative_activity"] == 50.0

    def test_tied_scores_partial(self):
        """一部同点のケース: 3人中2人が同点"""
        raw_scores = {
            1: {
                "legislative_activity": 10,
                "voting_behavior": 10,
                "policy_influence": 10,
                "transparency": 10,
                "question_quality": 10,
            },
            2: {
                "legislative_activity": 10,
                "voting_behavior": 10,
                "policy_influence": 10,
                "transparency": 10,
                "question_quality": 10,
            },
            3: {
                "legislative_activity": 20,
                "voting_behavior": 20,
                "policy_influence": 20,
                "transparency": 20,
                "question_quality": 20,
            },
        }
        normalized = {}
        _normalize_group(raw_scores, [1, 2, 3], normalized)
        # member 1 & 2: avg_rank = (0+1)/2 = 0.5, percentile = 0.5/(3-1)*100 = 25.0
        assert normalized[1]["legislative_activity"] == 25.0
        assert normalized[2]["legislative_activity"] == 25.0
        # member 3: rank 2, percentile = 2/(3-1)*100 = 100.0
        assert normalized[3]["legislative_activity"] == 100.0

    def test_empty_group(self):
        raw_scores = {}
        normalized = {}
        _normalize_group(raw_scores, [], normalized)
        assert len(normalized) == 0


class TestDefaultWeights:
    def test_weights_sum_to_one(self):
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_weight_values(self):
        assert DEFAULT_WEIGHTS["legislative_activity"] == 0.25
        assert DEFAULT_WEIGHTS["voting_behavior"] == 0.20
        assert DEFAULT_WEIGHTS["policy_influence"] == 0.20
        assert DEFAULT_WEIGHTS["transparency"] == 0.15
        assert DEFAULT_WEIGHTS["question_quality"] == 0.20
