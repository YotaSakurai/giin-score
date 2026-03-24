"""質問品質分析パイプライン

国会発言をLLMで分析し、質問の品質をスコアリングする。
イデオロギーフリーの原則に基づき、政策の方向性ではなく質問の「質」のみを評価。

バックエンド:
  - デフォルト: Ollama (ローカル、コスト無料)
  - 代替: Anthropic Claude API (SPEECH_QUALITY_BACKEND=anthropic)

使用例:
  python -m app.pipeline.runner --pipeline speech_quality --session 213
"""

import json
import logging
import os
import time

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.member import Member
from app.models.session import DietSession
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore

logger = logging.getLogger(__name__)

# バッチ設定
BATCH_SIZE = 20
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0
MAX_SPEECH_CHARS = 4000
MIN_SPEECH_CHARS = 200  # 200字未満の短い発言はスキップ
PARALLEL_WORKERS = int(os.environ.get("SPEECH_QUALITY_WORKERS", "4"))

# フィルタリング対象外のrole_category（答弁者・議長は質問者ではない）
SKIP_ROLE_CATEGORIES = {"cabinet", "chair"}

# LLMバックエンド設定
LLM_BACKEND = os.environ.get("SPEECH_QUALITY_BACKEND", "ollama")  # "ollama" or "anthropic"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")

SYSTEM_PROMPT = """\
あなたは国会質疑の品質を客観的に評価する分析システムです。

## 前提思想
国会の質疑時間は有限の国家資源である。この時間は国力の向上と国民生活の改善に直結する政策議論に使われるべきである。
政治家のスキャンダルや品性の問題と、政策立案能力は独立した評価軸であり、本システムは後者のみを評価する。

## 評価原則
1. **イデオロギーフリー**: 保守/リベラル等の政策の方向性は一切評価しない。「何を主張するか」ではなく「どれだけ実質的な政策議論ができているか」を評価する。
2. **与野党バイアス排除**: 与党・野党いずれの立場も有利不利なく評価する。
3. **発言の長さバイアス排除**: 短い質問でも鋭ければ高評価、長い質問でも冗長なら低評価。
4. **能力至上主義**: 政治家個人の不祥事・スキャンダルへの言及ではなく、制度・法律・予算を改善する能力の発揮度を評価する。

## 非生産的な質問の定義（低評価にすべきもの）
- スキャンダル追及のみの質問（裏金・不倫・失言等の追及に終始し、再発防止の制度改善提案を伴わない）
- 公開情報の確認質問（政府公表資料・答弁書・統計で確認できる事実をただ聞くだけ）
- パフォーマンス質問（メディア向けの見せ場作りが目的で、具体的な政策議論を伴わない）
- 繰り返し質問（既に答弁済みの内容を何度も聞き直す）
- 個人攻撃・揚げ足取り（政策ではなく人格を攻撃する質問）

## 生産的な質問の定義（高評価にすべきもの）
- 法律・予算・制度の具体的な改善提案を伴う質問
- 独自の調査・データ分析に基づく追及（公開情報の確認ではない）
- 行政の無駄・非効率を具体的に指摘し改善策を求める質問
- 国民生活・経済・安全保障に直接影響する政策課題の専門的議論
- 不祥事であっても、再発防止の法改正・制度設計を具体的に提案している場合は生産的

## 評価観点（各0-100点）
- **policy_relevance**: 法律・予算・制度の改善に直結する質問か。具体的な政策課題の議論は高評価。スキャンダル追及のみ（制度改善提案なし）は低評価。
- **constructiveness**: 具体的な改善提案・対案を伴う質問か。問題指摘+改善策の提示は高評価。批判のみ・個人攻撃は低評価。
- **expertise**: 独自の調査・専門知識に基づく質問か。データや事例を用いた分析的質問は高評価。公開情報をただ聞くだけ・表面的な一般論は低評価。
- **national_interest**: 国民生活の向上・国力強化に直結するテーマか。経済・安全保障・社会保障・教育等は高評価。内輪の政局話・ゴシップは低評価。

## 出力形式
以下のJSON形式のみを出力してください。JSON以外のテキストは一切出力しないでください。
{
  "policy_relevance": <0-100の整数>,
  "constructiveness": <0-100の整数>,
  "expertise": <0-100の整数>,
  "national_interest": <0-100の整数>,
  "summary": "<1文の評価要約（日本語）>"
}
"""


def _truncate_text(text: str, max_chars: int = MAX_SPEECH_CHARS) -> str:
    """発言テキストを最大文字数で切り詰める。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…（以下省略）"


def _build_user_message(speech_text: str, meeting_name: str | None) -> str:
    """分析用のユーザーメッセージを組み立てる。"""
    truncated = _truncate_text(speech_text)
    user_message = "以下の国会発言を評価してください。\n\n"
    if meeting_name:
        user_message += f"【会議名】{meeting_name}\n\n"
    user_message += f"【発言内容】\n{truncated}"
    return user_message


def _parse_llm_response(text: str) -> dict | None:
    """LLMレスポンスからJSONを抽出・バリデーションする。"""
    text = text.strip()
    if "{" not in text:
        logger.warning(f"No JSON found in response: {text[:100]}")
        return None

    try:
        json_str = text[text.index("{") : text.rindex("}") + 1]
        result = json.loads(json_str)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"JSON parse error: {e}")
        return None

    required_keys = [
        "policy_relevance",
        "constructiveness",
        "expertise",
        "national_interest",
    ]
    for key in required_keys:
        val = result.get(key)
        if not isinstance(val, (int, float)) or val < 0 or val > 100:
            result[key] = 50.0
        else:
            result[key] = float(val)

    return result


# ---------------------------------------------------------------------------
# Ollama バックエンド
# ---------------------------------------------------------------------------


def _analyze_speech_ollama(
    http_client: httpx.Client,
    speech_text: str,
    meeting_name: str | None,
) -> dict | None:
    """Ollama (ローカルLLM) で発言を分析する。"""
    user_message = _build_user_message(speech_text, meeting_name)

    for attempt in range(MAX_RETRIES):
        try:
            resp = http_client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 200},
                },
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("message", {}).get("content", "")
            result = _parse_llm_response(text)
            if result is not None:
                return result

            logger.warning(f"Failed to parse Ollama response (attempt {attempt + 1})")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY)
                continue
            return None

        except Exception as e:
            logger.error(f"Ollama error (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY * (2**attempt))
                continue
            return None

    return None


# ---------------------------------------------------------------------------
# Anthropic バックエンド
# ---------------------------------------------------------------------------


def _get_anthropic_client():
    """Anthropicクライアントを遅延初期化で取得する。"""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")
    return anthropic.Anthropic(api_key=api_key)


def _analyze_speech_anthropic(
    client,
    speech_text: str,
    meeting_name: str | None,
) -> dict | None:
    """Anthropic Claude API で発言を分析する。"""
    user_message = _build_user_message(speech_text, meeting_name)

    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            text = response.content[0].text
            result = _parse_llm_response(text)
            if result is not None:
                return result

            logger.warning(f"Failed to parse Anthropic response (attempt {attempt + 1})")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY)
                continue
            return None

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str or "overloaded" in error_str:
                delay = RETRY_BASE_DELAY * (2**attempt)
                logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1})")
                time.sleep(delay)
                continue
            logger.error(f"API error (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY * (2**attempt))
                continue
            return None

    return None


# ---------------------------------------------------------------------------
# メインパイプライン
# ---------------------------------------------------------------------------


def analyze_speeches_for_session(db: DBSession, session_number: int) -> int:
    """指定会期の発言品質を分析する。

    chair（議長・委員長）とcabinet（閣僚答弁）はスキップし、
    質問者（与野党議員）の実質的発言のみを分析対象とする。

    Returns:
        分析完了した発言数
    """
    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        logger.error(f"Session {session_number} not found")
        return 0

    # 未分析の発言を取得（フィルタリング適用）
    analyzed_ids_sq = db.query(SpeechQualityScore.speech_id).subquery()
    skip_member_ids_sq = (
        db.query(Member.id).filter(Member.role_category.in_(SKIP_ROLE_CATEGORIES)).subquery()
    )
    speeches = (
        db.query(Speech)
        .filter(
            Speech.session_id == diet_session.id,
            Speech.speech_chars >= MIN_SPEECH_CHARS,
            Speech.member_id.isnot(None),
            ~Speech.member_id.in_(db.query(skip_member_ids_sq)),
            ~Speech.id.in_(db.query(analyzed_ids_sq)),
        )
        .order_by(Speech.id)
        .all()
    )

    total = len(speeches)
    if total == 0:
        logger.info(f"No unanalyzed speeches found for session {session_number}")
        return 0

    backend = LLM_BACKEND.lower()
    logger.info(
        f"Analyzing {total} speeches for session {session_number} "
        f"(backend={backend}, workers={PARALLEL_WORKERS})"
    )

    # バックエンド初期化
    http_client = None
    anthropic_client = None

    if backend == "ollama":
        http_client = httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
            limits=httpx.Limits(max_connections=2, max_keepalive_connections=1),
        )
        try:
            r = http_client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
            r.raise_for_status()
            logger.info(f"Ollama connected: {OLLAMA_BASE_URL}, model={OLLAMA_MODEL}")
        except Exception as e:
            logger.error(f"Cannot connect to Ollama at {OLLAMA_BASE_URL}: {e}")
            http_client.close()
            return 0
    elif backend == "anthropic":
        anthropic_client = _get_anthropic_client()
    else:
        logger.error(f"Unknown backend: {backend}. Use 'ollama' or 'anthropic'.")
        return 0

    # http_clientは再接続で差し替えるためリストで保持
    clients = {"http": http_client, "anthropic": anthropic_client}

    def analyze_fn(text: str, name: str | None) -> dict | None:
        if backend == "ollama":
            return _analyze_speech_ollama(clients["http"], text, name)
        return _analyze_speech_anthropic(clients["anthropic"], text, name)

    processed = 0
    batch_count = 0
    start_time = time.time()

    # Discord通知（開始）
    from app.pipeline.notify import _send_webhook

    _send_webhook(
        {
            "title": "🔬 発言品質分析を開始します",
            "description": (
                f"**会期:** {session_number}\n"
                f"**対象発言数:** {total}件\n"
                f"**バックエンド:** {backend} ({PARALLEL_WORKERS}並列)"
            ),
            "color": 0x3498DB,
        }
    )

    # 通知間隔: 10バッチ(200件)ごと
    NOTIFY_EVERY_N_BATCHES = 10

    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 10

    try:
        for i in range(0, total, BATCH_SIZE):
            batch = speeches[i : i + BATCH_SIZE]
            batch_count += 1

            for speech in batch:
                if not speech.speech_text:
                    continue

                try:
                    result = analyze_fn(speech.speech_text, speech.meeting_name)
                except (httpx.ConnectError, httpx.ReadError, httpx.WriteError, httpx.PoolTimeout) as e:
                    logger.warning(f"Connection error (speech {speech.id}): {e}. Reconnecting...")
                    # httpxクライアント再接続
                    if backend == "ollama" and clients["http"]:
                        try:
                            clients["http"].close()
                        except Exception:
                            pass
                        clients["http"] = httpx.Client(
                            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
                            limits=httpx.Limits(max_connections=2, max_keepalive_connections=1),
                        )
                    time.sleep(5)
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        logger.error(f"{MAX_CONSECUTIVE_ERRORS} consecutive errors, aborting")
                        raise
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error (speech {speech.id}): {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        logger.error(f"{MAX_CONSECUTIVE_ERRORS} consecutive errors, aborting")
                        raise
                    continue

                if result is None:
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        logger.error(f"{MAX_CONSECUTIVE_ERRORS} consecutive None results, aborting")
                        break
                    continue

                consecutive_errors = 0  # 成功したらリセット

                overall = (
                    result["policy_relevance"]
                    + result["constructiveness"]
                    + result["expertise"]
                    + result["national_interest"]
                ) / 4.0

                quality_score = SpeechQualityScore(
                    speech_id=speech.id,
                    member_id=speech.member_id,
                    session_id=diet_session.id,
                    policy_relevance=result["policy_relevance"],
                    constructiveness=result["constructiveness"],
                    expertise=result["expertise"],
                    national_interest=result["national_interest"],
                    overall_quality=round(overall, 1),
                    analysis_summary=result.get("summary", ""),
                )
                db.add(quality_score)
                processed += 1

                if backend == "anthropic":
                    time.sleep(0.5)

            db.commit()

            elapsed = time.time() - start_time
            speed = processed / elapsed if elapsed > 0 else 0
            done = min(i + BATCH_SIZE, total)
            eta_hours = (total - done) / speed / 3600 if speed > 0 else 0
            logger.info(
                f"Batch {batch_count}: {done}/{total} "
                f"({speed:.1f} speeches/s, ETA: {eta_hours:.1f}h)"
            )

            # Discord途中経過通知
            if batch_count % NOTIFY_EVERY_N_BATCHES == 0:
                pct = done / total * 100
                _send_webhook(
                    {
                        "title": f"🔬 発言品質分析 {pct:.0f}%",
                        "description": (
                            f"**進捗:** {processed}/{total}件 分析済み\n"
                            f"**速度:** {speed:.1f} 件/秒\n"
                            f"**残り時間:** 約{eta_hours:.1f}時間"
                        ),
                        "color": 0x9B59B6,
                    }
                )
    finally:
        if backend == "ollama" and clients["http"]:
            clients["http"].close()

    elapsed = time.time() - start_time
    elapsed_h = elapsed / 3600
    logger.info(f"Completed: analyzed {processed}/{total} speeches in {elapsed_h:.1f}h")

    _send_webhook(
        {
            "title": "🎉 発言品質分析が完了しました",
            "description": (
                f"**会期:** {session_number}\n"
                f"**分析結果:** {processed}/{total}件\n"
                f"**所要時間:** {elapsed_h:.1f}時間"
            ),
            "color": 0x2ECC71,
        }
    )

    return processed


def compute_member_quality_scores(db: DBSession, session_number: int) -> dict[int, float]:
    """議員ごとの質問品質集約スコアを算出する。

    各議員の全発言品質スコアの平均を返す。

    Returns:
        {member_id: average_quality_score}
    """
    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        return {}

    results = (
        db.query(
            SpeechQualityScore.member_id,
            func.avg(SpeechQualityScore.overall_quality).label("avg_quality"),
            func.count(SpeechQualityScore.id).label("analyzed_count"),
        )
        .filter(SpeechQualityScore.session_id == diet_session.id)
        .group_by(SpeechQualityScore.member_id)
        .all()
    )

    member_scores = {}
    for row in results:
        member_scores[row.member_id] = round(float(row.avg_quality), 1)

    logger.info(f"Computed quality scores for {len(member_scores)} members")
    return member_scores
