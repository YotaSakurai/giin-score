"""speech_quality.py の LLM バックエンド・パイプラインフローのテスト

Ollama / Anthropic のAPIコールをモックし、analyze_speeches_for_session の
全分岐（成功・リトライ・エラー・品質ゲート）を網羅する。
"""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import httpx
import pytest
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.session import DietSession
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore
from app.pipeline.speech_quality import (
    LLMQualityTracker,
    _analyze_speech_anthropic,
    _analyze_speech_ollama,
    _get_anthropic_client,
    reset_quality_tracker,
)

VALID_LLM_JSON = json.dumps(
    {
        "policy_relevance": 75,
        "constructiveness": 60,
        "expertise": 55,
        "national_interest": 80,
        "summary": "テスト評価",
    }
)


def _make_ollama_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"message": {"content": content}},
        request=httpx.Request("POST", "https://example.com"),
    )


# =====================================================================
# _analyze_speech_ollama
# =====================================================================


class TestAnalyzeSpeechOllama:
    def setup_method(self):
        reset_quality_tracker()

    @patch("app.pipeline.speech_quality.time.sleep")
    def test_success(self, mock_sleep):
        mock_client = MagicMock()
        mock_client.post.return_value = _make_ollama_response(VALID_LLM_JSON)

        result = _analyze_speech_ollama(mock_client, "テスト発言" * 50, "予算委員会")
        assert result is not None
        assert result["policy_relevance"] == 75

    @patch("app.pipeline.speech_quality.time.sleep")
    def test_parse_failure_retry(self, mock_sleep):
        """パース失敗→リトライ→成功。"""
        mock_client = MagicMock()
        mock_client.post.side_effect = [
            _make_ollama_response("invalid response"),
            _make_ollama_response(VALID_LLM_JSON),
        ]

        result = _analyze_speech_ollama(mock_client, "テスト", None)
        assert result is not None
        assert mock_client.post.call_count == 2

    @patch("app.pipeline.speech_quality.time.sleep")
    def test_all_retries_fail(self, mock_sleep):
        """全リトライ失敗→None。"""
        mock_client = MagicMock()
        mock_client.post.return_value = _make_ollama_response("bad")

        result = _analyze_speech_ollama(mock_client, "テスト", None)
        assert result is None

    @patch("app.pipeline.speech_quality.time.sleep")
    def test_http_error_retry(self, mock_sleep):
        """HTTPエラー→リトライ。"""
        mock_client = MagicMock()
        mock_client.post.side_effect = [
            Exception("connection refused"),
            _make_ollama_response(VALID_LLM_JSON),
        ]

        result = _analyze_speech_ollama(mock_client, "テスト", None)
        assert result is not None

    @patch("app.pipeline.speech_quality.time.sleep")
    def test_all_http_errors(self, mock_sleep):
        """全リトライHTTPエラー→None。"""
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("connection refused")

        result = _analyze_speech_ollama(mock_client, "テスト", None)
        assert result is None


# =====================================================================
# _analyze_speech_anthropic
# =====================================================================


class TestAnalyzeSpeechAnthropic:
    def setup_method(self):
        reset_quality_tracker()

    @patch("app.pipeline.speech_quality.time.sleep")
    def test_success(self, mock_sleep):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=VALID_LLM_JSON)]
        mock_client.messages.create.return_value = mock_response

        result = _analyze_speech_anthropic(mock_client, "テスト発言", "委員会")
        assert result is not None
        assert result["expertise"] == 55

    @patch("app.pipeline.speech_quality.time.sleep")
    def test_rate_limit_retry(self, mock_sleep):
        """429レート制限→リトライ→成功。"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=VALID_LLM_JSON)]

        mock_client.messages.create.side_effect = [
            Exception("429 rate limit exceeded"),
            mock_response,
        ]

        result = _analyze_speech_anthropic(mock_client, "テスト", None)
        assert result is not None

    @patch("app.pipeline.speech_quality.time.sleep")
    def test_overloaded_retry(self, mock_sleep):
        """overloaded→リトライ→成功。"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=VALID_LLM_JSON)]

        mock_client.messages.create.side_effect = [
            Exception("overloaded"),
            mock_response,
        ]

        result = _analyze_speech_anthropic(mock_client, "テスト", None)
        assert result is not None

    @patch("app.pipeline.speech_quality.time.sleep")
    def test_all_retries_fail(self, mock_sleep):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("server error")

        result = _analyze_speech_anthropic(mock_client, "テスト", None)
        assert result is None

    @patch("app.pipeline.speech_quality.time.sleep")
    def test_parse_failure(self, mock_sleep):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="not json")]
        mock_client.messages.create.return_value = mock_response

        result = _analyze_speech_anthropic(mock_client, "テスト", None)
        assert result is None


# =====================================================================
# _get_anthropic_client
# =====================================================================


class TestGetAnthropicClient:
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False)
    def test_no_api_key(self):
        try:
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                _get_anthropic_client()
        except ImportError:
            pytest.skip("anthropic package not installed")


# =====================================================================
# LLMQualityTracker
# =====================================================================


class TestLLMQualityTracker:
    def test_no_responses(self):
        t = LLMQualityTracker()
        assert t.failure_rate == 0.0
        assert not t.should_warn()
        assert not t.should_abort()

    def test_warn_threshold(self):
        t = LLMQualityTracker(warn_threshold=0.10)
        for _ in range(9):
            t.record_success()
        t.record_failure()
        # 10 responses, 10% failure rate
        assert t.should_warn()
        assert not t.should_abort()

    def test_abort_threshold(self):
        t = LLMQualityTracker(abort_threshold=0.25)
        for _ in range(15):
            t.record_success()
        for _ in range(5):
            t.record_failure()
        # 20 responses, 25% failure rate
        assert t.should_abort()

    def test_record_fallback(self):
        t = LLMQualityTracker()
        t.record_fallback("policy_relevance", -5)
        assert t.fallback_count == 1

    def test_summary(self):
        t = LLMQualityTracker()
        t.record_success()
        t.record_failure()
        s = t.summary()
        assert "total=2" in s
        assert "failed=1" in s


# =====================================================================
# analyze_speeches_for_session (メインパイプライン)
# =====================================================================


class TestAnalyzeSpeechesForSession:
    def _seed_speeches(self, db: Session, count: int = 3):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()

        for i in range(1, count + 1):
            db.add(
                Member(
                    id=i,
                    name=f"議員{i}",
                    chamber="representatives",
                    role_category="member",
                )
            )
        db.flush()

        for i in range(1, count + 1):
            db.add(
                Speech(
                    id=i,
                    session_id=1,
                    member_id=i,
                    meeting_name="予算委員会",
                    speech_text="政策に関する質問" * 100,
                    speech_chars=600,
                    speech_date=date(2024, 1, i),
                )
            )
        db.commit()

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.time.sleep")
    def test_ollama_success(self, mock_sleep, mock_webhook, db: Session):
        """Ollamaバックエンドで正常分析。"""
        from app.pipeline.speech_quality import analyze_speeches_for_session

        self._seed_speeches(db)

        mock_http = MagicMock()
        # tags エンドポイント
        mock_http.get.return_value = httpx.Response(
            200,
            json={},
            request=httpx.Request("GET", "https://example.com"),
        )
        # 分析API
        mock_http.post.return_value = _make_ollama_response(VALID_LLM_JSON)
        mock_http.close = MagicMock()

        with (
            patch("app.pipeline.speech_quality.LLM_BACKEND", "ollama"),
            patch("app.pipeline.speech_quality.httpx.Client", return_value=mock_http),
        ):
            result = analyze_speeches_for_session(db, 215)

        assert result == 3
        assert db.query(SpeechQualityScore).count() == 3

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.time.sleep")
    def test_anthropic_success(self, mock_sleep, mock_webhook, db: Session):
        """Anthropicバックエンドで正常分析。"""
        from app.pipeline.speech_quality import analyze_speeches_for_session

        self._seed_speeches(db)

        mock_anthropic = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=VALID_LLM_JSON)]
        mock_anthropic.messages.create.return_value = mock_response

        with (
            patch("app.pipeline.speech_quality.LLM_BACKEND", "anthropic"),
            patch("app.pipeline.speech_quality._get_anthropic_client", return_value=mock_anthropic),
        ):
            result = analyze_speeches_for_session(db, 215)

        assert result == 3

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.time.sleep")
    def test_session_not_found(self, mock_sleep, mock_webhook, db: Session):
        from app.pipeline.speech_quality import analyze_speeches_for_session

        assert analyze_speeches_for_session(db, 999) == 0

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.time.sleep")
    def test_no_speeches(self, mock_sleep, mock_webhook, db: Session):
        from app.pipeline.speech_quality import analyze_speeches_for_session

        db.add(DietSession(id=1, session_number=215, kind="通常"))
        db.commit()
        assert analyze_speeches_for_session(db, 215) == 0

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.time.sleep")
    def test_ollama_connection_fail(self, mock_sleep, mock_webhook, db: Session):
        """Ollama接続失敗時に0を返す。"""
        from app.pipeline.speech_quality import analyze_speeches_for_session

        self._seed_speeches(db)

        mock_http = MagicMock()
        mock_http.get.side_effect = Exception("connection refused")
        mock_http.close = MagicMock()

        with (
            patch("app.pipeline.speech_quality.LLM_BACKEND", "ollama"),
            patch("app.pipeline.speech_quality.httpx.Client", return_value=mock_http),
        ):
            result = analyze_speeches_for_session(db, 215)

        assert result == 0

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.time.sleep")
    def test_unknown_backend(self, mock_sleep, mock_webhook, db: Session):
        """不明なバックエンドで0を返す。"""
        from app.pipeline.speech_quality import analyze_speeches_for_session

        self._seed_speeches(db)

        with patch("app.pipeline.speech_quality.LLM_BACKEND", "unknown"):
            result = analyze_speeches_for_session(db, 215)

        assert result == 0

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.time.sleep")
    def test_connection_error_reconnect(self, mock_sleep, mock_webhook, db: Session):
        """ConnectError時にリコネクトして続行。"""
        from app.pipeline.speech_quality import analyze_speeches_for_session

        self._seed_speeches(db, count=2)

        mock_http = MagicMock()
        mock_http.get.return_value = httpx.Response(
            200,
            json={},
            request=httpx.Request("GET", "https://example.com"),
        )
        # 1回目ConnectError、2回目以降は成功
        mock_http.post.side_effect = [
            httpx.ConnectError("refused"),
            _make_ollama_response(VALID_LLM_JSON),
        ]
        mock_http.close = MagicMock()

        new_client = MagicMock()
        new_client.post.return_value = _make_ollama_response(VALID_LLM_JSON)
        new_client.close = MagicMock()

        call_count = [0]

        def mock_client_factory(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_http
            return new_client

        with (
            patch("app.pipeline.speech_quality.LLM_BACKEND", "ollama"),
            patch("app.pipeline.speech_quality.httpx.Client", side_effect=mock_client_factory),
        ):
            result = analyze_speeches_for_session(db, 215)

        # 少なくとも1件は処理される
        assert result >= 1

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.time.sleep")
    def test_skips_chair_and_cabinet(self, mock_sleep, mock_webhook, db: Session):
        """chair/cabinetロールの議員はスキップされる。"""
        from app.pipeline.speech_quality import analyze_speeches_for_session

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()

        db.add(Member(id=1, name="委員長", chamber="representatives", role_category="chair"))
        db.add(Member(id=2, name="大臣", chamber="representatives", role_category="cabinet"))
        db.add(Member(id=3, name="質問者", chamber="representatives", role_category="member"))
        db.flush()

        for mid in [1, 2, 3]:
            db.add(
                Speech(
                    id=mid,
                    session_id=1,
                    member_id=mid,
                    meeting_name="委員会",
                    speech_text="テスト" * 100,
                    speech_chars=400,
                )
            )
        db.commit()

        mock_http = MagicMock()
        mock_http.get.return_value = httpx.Response(
            200,
            json={},
            request=httpx.Request("GET", "https://example.com"),
        )
        mock_http.post.return_value = _make_ollama_response(VALID_LLM_JSON)
        mock_http.close = MagicMock()

        with (
            patch("app.pipeline.speech_quality.LLM_BACKEND", "ollama"),
            patch("app.pipeline.speech_quality.httpx.Client", return_value=mock_http),
        ):
            result = analyze_speeches_for_session(db, 215)

        # member_id=3（質問者）のみ分析される
        assert result == 1

    @patch("app.pipeline.notify._send_webhook")
    @patch("app.pipeline.speech_quality.time.sleep")
    def test_procedural_speech_skipped(self, mock_sleep, mock_webhook, db: Session):
        """議事進行発言はスキップされる。"""
        from app.pipeline.speech_quality import analyze_speeches_for_session

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        db.add(Member(id=1, name="議員", chamber="representatives", role_category="member"))
        db.flush()

        db.add(
            Speech(
                id=1,
                session_id=1,
                member_id=1,
                meeting_name="委員会",
                speech_text="これより本日の会議を開きます。" + "あ" * 300,
                speech_chars=400,
            )
        )
        db.add(
            Speech(
                id=2,
                session_id=1,
                member_id=1,
                meeting_name="委員会",
                speech_text="政策についての実質的な質問" * 50,
                speech_chars=400,
            )
        )
        db.commit()

        mock_http = MagicMock()
        mock_http.get.return_value = httpx.Response(
            200,
            json={},
            request=httpx.Request("GET", "https://example.com"),
        )
        mock_http.post.return_value = _make_ollama_response(VALID_LLM_JSON)
        mock_http.close = MagicMock()

        with (
            patch("app.pipeline.speech_quality.LLM_BACKEND", "ollama"),
            patch("app.pipeline.speech_quality.httpx.Client", return_value=mock_http),
        ):
            result = analyze_speeches_for_session(db, 215)

        # 議事進行発言はスキップ、実質的発言のみ分析
        assert result == 1
