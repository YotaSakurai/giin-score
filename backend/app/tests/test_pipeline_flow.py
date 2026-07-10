"""LLMパイプラインフローテスト

speech_quality.py の analyze_speeches_for_session フローを
LLM HTTP呼び出しのみスタブし、それ以外のビジネスロジック
（フィルタリング・パース・DB保存・品質ゲート）は全て実物で動かす。
"""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.session import DietSession
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore
from app.pipeline.speech_quality import (
    LLMQualityTracker,
    _build_user_message,
    _is_procedural,
    _parse_llm_response,
    _truncate_text,
    analyze_speeches_for_session,
    compute_member_quality_scores,
    reset_quality_tracker,
)

# =====================================================================
# ユーティリティ関数テスト
# =====================================================================


class TestTruncateText:
    def test_short_text_unchanged(self):
        text = "短いテキスト"
        assert _truncate_text(text) == text

    def test_long_text_truncated(self):
        text = "あ" * 5000
        result = _truncate_text(text)
        assert len(result) < 5000
        assert result.endswith("…（以下省略）")

    def test_exact_boundary(self):
        text = "a" * 4000
        assert _truncate_text(text) == text

    def test_custom_max(self):
        text = "a" * 200
        result = _truncate_text(text, max_chars=100)
        assert len(result) < 200
        assert result.endswith("…（以下省略）")


class TestBuildUserMessage:
    def test_with_meeting_name(self):
        msg = _build_user_message("発言内容", "予算委員会")
        assert "予算委員会" in msg
        assert "発言内容" in msg

    def test_without_meeting_name(self):
        msg = _build_user_message("発言内容", None)
        assert "発言内容" in msg
        assert "【会議名】" not in msg

    def test_truncates_long_speech(self):
        long_text = "あ" * 5000
        msg = _build_user_message(long_text, None)
        assert "…（以下省略）" in msg


# =====================================================================
# フィルタリングロジックの追加テスト
# =====================================================================


class TestProceduralDetection:
    """議事進行発言の検出テスト (canary tests を補完)。"""

    def test_government_reference_person(self):
        assert _is_procedural("○政府参考人（山田太郎君）　はい。")

    def test_reference_person_answer(self):
        assert _is_procedural("○参考人（鈴木一郎君）　ありがとう。")

    def test_speed_record_instruction(self):
        # 「起こして」は regex (止め|起こ)してください にマッチ
        text = "速記を起こしてください。" + "あ" * 200
        assert _is_procedural(text)

    def test_committee_member_change(self):
        assert _is_procedural("委員の異動について御報告いたします。")

    def test_substantive_question_not_procedural(self):
        text = "○佐藤太郎君　少子化対策について、具体的な財源確保策をお示しください。"
        assert not _is_procedural(text)


# =====================================================================
# LLM品質ゲートの詳細テスト
# =====================================================================


class TestLLMQualityTracker:
    def test_fresh_tracker(self):
        t = LLMQualityTracker()
        assert t.failure_rate == 0.0
        assert not t.should_warn()
        assert not t.should_abort()

    def test_warn_threshold(self):
        t = LLMQualityTracker(warn_threshold=0.10)
        for _ in range(9):
            t.record_success()
        t.record_failure()
        # 10 total, 10% failure → should warn
        assert t.should_warn()

    def test_no_warn_below_min_samples(self):
        t = LLMQualityTracker(warn_threshold=0.10)
        t.record_failure()
        # 1 total, 100% failure but < 10 samples
        assert not t.should_warn()

    def test_abort_threshold(self):
        t = LLMQualityTracker(abort_threshold=0.25)
        for _ in range(15):
            t.record_success()
        for _ in range(5):
            t.record_failure()
        # 20 total, 25% failure → should abort
        assert t.should_abort()

    def test_summary_format(self):
        t = LLMQualityTracker()
        t.record_success()
        t.record_failure()
        s = t.summary()
        assert "total=2" in s
        assert "failed=1" in s

    def test_fallback_tracking(self):
        t = LLMQualityTracker()
        t.record_fallback("policy_relevance", -10)
        assert t.fallback_count == 1


# =====================================================================
# パイプラインフロー統合テスト
# =====================================================================


def _make_valid_llm_response(pr=70, co=65, ex=60, ni=75, summary="テスト要約"):
    """有効なLLMレスポンスJSONを返す。"""
    return json.dumps(
        {
            "policy_relevance": pr,
            "constructiveness": co,
            "expertise": ex,
            "national_interest": ni,
            "summary": summary,
        }
    )


@pytest.fixture()
def pipeline_seed(db: Session):
    """パイプラインテスト用のシードデータ。"""
    session = DietSession(id=1, session_number=215, kind="通常")
    db.add(session)
    db.flush()

    members = [
        Member(
            id=1,
            name="質問者A",
            chamber="representatives",
            party="自由民主党",
            role_category="ruling_junior",
        ),
        Member(
            id=2,
            name="質問者B",
            chamber="representatives",
            party="立憲民主党",
            role_category="opposition_senior",
        ),
        Member(
            id=3,
            name="大臣C",
            chamber="representatives",
            party="自由民主党",
            role_category="cabinet",
        ),
        Member(
            id=4,
            name="議長D",
            chamber="representatives",
            party="自由民主党",
            role_category="chair",
        ),
    ]
    db.add_all(members)
    db.flush()

    substantive = "あ" * 300  # MIN_SPEECH_CHARS以上
    short_text = "あ" * 50  # 短すぎてスキップ
    procedural = "○委員長（山田太郎君）　これより会議を開きます。" + "あ" * 300

    speeches = [
        # 質問者Aの実質的発言 (分析対象)
        Speech(
            id=1,
            session_id=1,
            member_id=1,
            meeting_name="予算委員会",
            speech_date=date(2024, 2, 15),
            speech_text=substantive,
            speech_chars=300,
        ),
        # 質問者Bの実質的発言 (分析対象)
        Speech(
            id=2,
            session_id=1,
            member_id=2,
            meeting_name="厚生労働委員会",
            speech_date=date(2024, 2, 16),
            speech_text=substantive,
            speech_chars=300,
        ),
        # 短い発言 (スキップ: MIN_SPEECH_CHARS未満)
        Speech(
            id=3,
            session_id=1,
            member_id=1,
            meeting_name="予算委員会",
            speech_text=short_text,
            speech_chars=50,
        ),
        # 大臣の答弁 (スキップ: cabinet)
        Speech(
            id=4,
            session_id=1,
            member_id=3,
            meeting_name="予算委員会",
            speech_text=substantive,
            speech_chars=300,
        ),
        # 議長の発言 (スキップ: chair)
        Speech(
            id=5,
            session_id=1,
            member_id=4,
            meeting_name="予算委員会",
            speech_text=substantive,
            speech_chars=300,
        ),
        # 議事進行発言 (パイプライン内でスキップ)
        Speech(
            id=6,
            session_id=1,
            member_id=1,
            meeting_name="予算委員会",
            speech_text=procedural,
            speech_chars=350,
        ),
    ]
    db.add_all(speeches)
    db.commit()
    return session


class TestAnalyzeSpeechesFlow:
    """analyze_speeches_for_session の統合テスト。

    LLM HTTP呼び出しのみスタブし、フィルタリング・パース・
    DB保存・品質ゲートは全て実物で実行する。
    """

    def _mock_ollama_response(self, pr=70, co=65, ex=60, ni=75):
        """Ollama APIのモックレスポンスを作成。"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "message": {"content": _make_valid_llm_response(pr, co, ex, ni)}
        }
        return mock_resp

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.httpx.Client")
    def test_full_flow_filters_correctly(self, mock_client_cls, mock_webhook, db, pipeline_seed):
        """フィルタリング後、実質的発言のみ分析される。"""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        # tags endpoint (接続確認)
        tags_resp = MagicMock()
        tags_resp.raise_for_status = MagicMock()
        # post endpoint (分析)
        analyze_resp = self._mock_ollama_response()
        mock_client.get.return_value = tags_resp
        mock_client.post.return_value = analyze_resp

        reset_quality_tracker()
        result = analyze_speeches_for_session(db, 215)

        # speech 1, 2 が分析対象 (3=短い, 4=cabinet, 5=chair, 6=議事進行)
        # speech 6 は procedural なのでパイプライン内でスキップ
        # DB上はspeech_charsとrole_categoryフィルタで 1,2,6 が候補
        # 6 は _is_procedural でスキップ → 実際の分析は2件
        assert result == 2

        # DBに保存されている
        saved = db.query(SpeechQualityScore).all()
        assert len(saved) == 2

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.httpx.Client")
    def test_scores_saved_correctly(self, mock_client_cls, mock_webhook, db, pipeline_seed):
        """分析結果がDBに正しく保存される。"""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        tags_resp = MagicMock()
        tags_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = tags_resp
        mock_client.post.return_value = self._mock_ollama_response(pr=80, co=70, ex=60, ni=90)

        reset_quality_tracker()
        analyze_speeches_for_session(db, 215)

        scores = db.query(SpeechQualityScore).all()
        for s in scores:
            assert s.policy_relevance == 80
            assert s.constructiveness == 70
            assert s.expertise == 60
            assert s.national_interest == 90
            expected_overall = (80 + 70 + 60 + 90) / 4.0
            assert abs(s.overall_quality - expected_overall) < 0.1

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.httpx.Client")
    def test_already_analyzed_skipped(self, mock_client_cls, mock_webhook, db, pipeline_seed):
        """既に分析済みの発言は再分析されない。"""
        # speech 1 を事前に分析済みにする
        existing = SpeechQualityScore(
            speech_id=1,
            member_id=1,
            session_id=1,
            policy_relevance=50,
            constructiveness=50,
            expertise=50,
            national_interest=50,
            overall_quality=50.0,
        )
        db.add(existing)
        db.commit()

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        tags_resp = MagicMock()
        tags_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = tags_resp
        mock_client.post.return_value = self._mock_ollama_response()

        reset_quality_tracker()
        result = analyze_speeches_for_session(db, 215)

        # speech 2 のみ新規分析
        assert result == 1

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.httpx.Client")
    def test_quality_gate_abort(self, mock_client_cls, mock_webhook, db, pipeline_seed):
        """LLM品質ゲートが発動するとパイプラインが停止する。"""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        tags_resp = MagicMock()
        tags_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = tags_resp

        # 全てのLLM応答を不正なJSONにする
        bad_resp = MagicMock()
        bad_resp.status_code = 200
        bad_resp.raise_for_status = MagicMock()
        bad_resp.json.return_value = {"message": {"content": "I cannot analyze this."}}
        mock_client.post.return_value = bad_resp

        reset_quality_tracker()
        result = analyze_speeches_for_session(db, 215)

        # 全てパース失敗 → 保存0件
        assert result == 0
        saved = db.query(SpeechQualityScore).all()
        assert len(saved) == 0

    def test_session_not_found(self, db, pipeline_seed):
        result = analyze_speeches_for_session(db, 999)
        assert result == 0


# =====================================================================
# 議員品質スコア集約テスト
# =====================================================================


class TestComputeMemberQualityScores:
    def test_aggregation(self, db: Session, pipeline_seed):
        """発言品質スコアが議員ごとに正しく集約される。"""
        # 手動でスコアをシード
        scores = [
            SpeechQualityScore(
                speech_id=1,
                member_id=1,
                session_id=1,
                policy_relevance=80,
                constructiveness=70,
                expertise=60,
                national_interest=90,
                overall_quality=75.0,
            ),
            SpeechQualityScore(
                speech_id=2,
                member_id=2,
                session_id=1,
                policy_relevance=90,
                constructiveness=85,
                expertise=80,
                national_interest=88,
                overall_quality=85.8,
            ),
        ]
        db.add_all(scores)
        db.commit()

        result = compute_member_quality_scores(db, 215)

        assert 1 in result
        assert 2 in result
        assert result[1] == 75.0
        assert result[2] == 85.8

    def test_multiple_speeches_averaged(self, db: Session, pipeline_seed):
        """同一議員の複数発言は平均化される。"""
        # member 1 に2つのスコア
        db.add(
            SpeechQualityScore(
                speech_id=1,
                member_id=1,
                session_id=1,
                policy_relevance=80,
                constructiveness=80,
                expertise=80,
                national_interest=80,
                overall_quality=80.0,
            )
        )
        # speech_id=6 も member_id=1
        db.add(
            SpeechQualityScore(
                speech_id=6,
                member_id=1,
                session_id=1,
                policy_relevance=60,
                constructiveness=60,
                expertise=60,
                national_interest=60,
                overall_quality=60.0,
            )
        )
        db.commit()

        result = compute_member_quality_scores(db, 215)
        assert result[1] == 70.0  # (80 + 60) / 2

    def test_session_not_found(self, db: Session, pipeline_seed):
        result = compute_member_quality_scores(db, 999)
        assert result == {}

    def test_no_scores_returns_empty(self, db: Session, pipeline_seed):
        result = compute_member_quality_scores(db, 215)
        assert result == {}


# =====================================================================
# パースロジック追加テスト (canary を補完)
# =====================================================================


class TestParseResponseEdgeCases:
    """_parse_llm_response のエッジケース。"""

    def setup_method(self):
        reset_quality_tracker()

    def test_json_with_surrounding_text(self):
        text = (
            "はい、分析結果です。\n"
            '{"policy_relevance": 70, "constructiveness": 65, '
            '"expertise": 60, "national_interest": 75, '
            '"summary": "良い質問"}\n以上です。'
        )
        result = _parse_llm_response(text)
        assert result is not None
        assert result["policy_relevance"] == 70

    def test_negative_score_fallback(self):
        text = json.dumps(
            {
                "policy_relevance": -10,
                "constructiveness": 65,
                "expertise": 60,
                "national_interest": 75,
            }
        )
        result = _parse_llm_response(text)
        assert result is not None
        assert result["policy_relevance"] == 50.0  # フォールバック

    def test_over_100_score_fallback(self):
        text = json.dumps(
            {
                "policy_relevance": 150,
                "constructiveness": 65,
                "expertise": 60,
                "national_interest": 75,
            }
        )
        result = _parse_llm_response(text)
        assert result is not None
        assert result["policy_relevance"] == 50.0

    def test_string_score_fallback(self):
        text = json.dumps(
            {
                "policy_relevance": "high",
                "constructiveness": 65,
                "expertise": 60,
                "national_interest": 75,
            }
        )
        result = _parse_llm_response(text)
        assert result is not None
        assert result["policy_relevance"] == 50.0

    def test_missing_key_fallback(self):
        text = json.dumps(
            {
                "constructiveness": 65,
                "expertise": 60,
                "national_interest": 75,
            }
        )
        result = _parse_llm_response(text)
        assert result is not None
        assert result["policy_relevance"] == 50.0

    def test_empty_string(self):
        result = _parse_llm_response("")
        assert result is None

    def test_malformed_json(self):
        result = _parse_llm_response("{broken json")
        assert result is None
