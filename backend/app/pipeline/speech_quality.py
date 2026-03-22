"""質問品質分析パイプライン

国会発言をClaude Haiku で分析し、質問の品質をスコアリングする。
イデオロギーフリーの原則に基づき、政策の方向性ではなく質問の「質」のみを評価。

使用例:
  python -m app.pipeline.runner --pipeline speech_quality --session 213
"""

import json
import logging
import os
import time

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.session import DietSession
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore

logger = logging.getLogger(__name__)

# バッチ設定
BATCH_SIZE = 20  # 一度にAPIに送る件数
API_RATE_LIMIT_DELAY = 0.5  # API呼び出し間隔（秒）
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # リトライ間隔の基底（秒）
MAX_SPEECH_CHARS = 4000  # LLMに送る発言テキストの最大文字数

SYSTEM_PROMPT = """\
あなたは国会質疑の品質を客観的に評価する分析システムです。
以下の原則に厳密に従ってください:

## 評価原則
1. **イデオロギーフリー**: 政策の方向性（保守/リベラル等）は一切評価しない。質問の「質」のみを評価する。
2. **与野党バイアス排除**: 野党の追及型質問、与党の政策説明型質問、いずれも質問の質で評価する。追及すること自体は低評価にしない。
3. **発言の長さバイアス排除**: 短い質問でも鋭ければ高評価、長い質問でも冗長なら低評価。
4. **「時間の無駄」の定義**: 同じ質問の繰り返し、関係ない話題への脱線、事実に基づかない主張、パフォーマンス目的の質問。

## 評価観点（各0-100点）
- **policy_relevance**: 具体的な政策課題に関する質問か。法律・予算・制度に関する具体的な議論は高評価。
- **constructiveness**: 建設的な提案・追及か。問題点の指摘と改善提案があれば高評価。揚げ足取りや個人攻撃は低評価。
- **expertise**: 専門知識に基づく質問か。データや事例を用いた質問は高評価。表面的な一般論は低評価。
- **national_interest**: 国民生活・国益に直接関わるテーマか。社会問題・経済・安全保障等は高評価。内輪の政局話は低評価。

## 出力形式（JSON）
{
  "policy_relevance": <0-100>,
  "constructiveness": <0-100>,
  "expertise": <0-100>,
  "national_interest": <0-100>,
  "summary": "<1文の評価要約（日本語）>"
}
"""


def _get_anthropic_client():
    """Anthropicクライアントを遅延初期化で取得する。"""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")
    return anthropic.Anthropic(api_key=api_key)


def _truncate_text(text: str, max_chars: int = MAX_SPEECH_CHARS) -> str:
    """発言テキストを最大文字数で切り詰める。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…（以下省略）"


def _analyze_speech(client, speech_text: str, meeting_name: str | None) -> dict | None:
    """単一の発言をClaude Haikuで分析する。"""
    truncated = _truncate_text(speech_text)

    user_message = "以下の国会発言を評価してください。\n\n"
    if meeting_name:
        user_message += f"【会議名】{meeting_name}\n\n"
    user_message += f"【発言内容】\n{truncated}"

    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            text = response.content[0].text.strip()
            # JSON部分を抽出
            if "{" in text:
                json_str = text[text.index("{") : text.rindex("}") + 1]
                result = json.loads(json_str)

                # バリデーション
                required_keys = [
                    "policy_relevance",
                    "constructiveness",
                    "expertise",
                    "national_interest",
                ]
                for key in required_keys:
                    val = result.get(key)
                    if not isinstance(val, (int, float)) or val < 0 or val > 100:
                        result[key] = 50.0  # 不正値はデフォルト
                    else:
                        result[key] = float(val)

                return result

            logger.warning(f"No JSON found in response: {text[:100]}")
            return None

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY * (2**attempt))
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


def analyze_speeches_for_session(db: Session, session_number: int) -> int:
    """指定会期の発言品質を分析する。

    Returns:
        分析完了した発言数
    """
    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        logger.error(f"Session {session_number} not found")
        return 0

    # 未分析の発言を取得（既に分析済みのspeech_idを除外）
    analyzed_ids_sq = db.query(SpeechQualityScore.speech_id).subquery()
    speeches = (
        db.query(Speech)
        .filter(
            Speech.session_id == diet_session.id,
            Speech.speech_chars >= 100,  # 100文字未満は短すぎるのでスキップ
            ~Speech.id.in_(db.query(analyzed_ids_sq)),
        )
        .order_by(Speech.id)
        .all()
    )

    total = len(speeches)
    if total == 0:
        logger.info(f"No unanalyzed speeches found for session {session_number}")
        return 0

    logger.info(f"Analyzing {total} speeches for session {session_number}")

    client = _get_anthropic_client()
    processed = 0
    batch_count = 0

    for i in range(0, total, BATCH_SIZE):
        batch = speeches[i : i + BATCH_SIZE]
        batch_count += 1

        for speech in batch:
            if not speech.speech_text:
                continue

            result = _analyze_speech(client, speech.speech_text, speech.meeting_name)
            if result is None:
                continue

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

            # レート制限
            time.sleep(API_RATE_LIMIT_DELAY)

        # バッチごとにコミット
        db.commit()
        logger.info(f"Batch {batch_count}: processed {min(i + BATCH_SIZE, total)}/{total}")

    logger.info(f"Completed: analyzed {processed}/{total} speeches")
    return processed


def compute_member_quality_scores(db: Session, session_number: int) -> dict[int, float]:
    """議員ごとの質問品質集約スコアを算出する。

    各議員の全発言品質スコアの加重平均を返す。
    発言文字数で重み付け（長い発言ほど重要度が高い）。

    Returns:
        {member_id: average_quality_score}
    """
    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        return {}

    # 議員ごとの品質スコアを取得（発言文字数を重みとして使用）
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
