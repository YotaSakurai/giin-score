"""Discord Webhook通知ユーティリティ (fire-and-forget)"""

import logging
from datetime import UTC, datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _send_webhook(embed: dict) -> None:
    """Discord Webhookにembedを送信する。失敗してもログのみで例外を投げない。"""
    url = settings.discord_webhook_url
    if not url:
        return
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json={"embeds": [embed]})
            resp.raise_for_status()
    except Exception:
        logger.warning("Discord webhook送信に失敗しました", exc_info=True)


def notify_batch_start(session_number: int, pipelines: list[str]) -> None:
    """バッチ開始通知"""
    pipeline_list = "\n".join(f"・{p}" for p in pipelines)
    _send_webhook(
        {
            "title": "パイプライン定期実行を開始します",
            "description": (f"**会期:** {session_number}\n**対象パイプライン:**\n{pipeline_list}"),
            "color": 0x3498DB,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


def notify_pipeline_success(name: str, records: int, elapsed: float) -> None:
    """個別パイプライン成功通知"""
    _send_webhook(
        {
            "title": f"✅ {name} 完了",
            "description": f"**処理件数:** {records}件\n**所要時間:** {elapsed:.1f}秒",
            "color": 0x2ECC71,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


def notify_pipeline_failure(name: str, error: str, elapsed: float) -> None:
    """個別パイプライン失敗通知"""
    truncated = error[:500] if len(error) > 500 else error
    _send_webhook(
        {
            "title": f"❌ {name} 失敗",
            "description": (f"**エラー:** ```{truncated}```\n**所要時間:** {elapsed:.1f}秒"),
            "color": 0xE74C3C,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


def notify_batch_complete(
    session_number: int,
    results: list[dict],
    total_elapsed: float,
) -> None:
    """バッチ完了サマリー通知"""
    success_count = sum(1 for r in results if r["status"] == "ok")
    fail_count = sum(1 for r in results if r["status"] == "error")

    lines = []
    for r in results:
        if r["status"] == "ok":
            lines.append(f"✅ **{r['name']}** — {r['records']}件 ({r['elapsed']:.1f}秒)")
        else:
            lines.append(f"❌ **{r['name']}** — {r['error']}")

    if fail_count == 0:
        title = f"🎉 全パイプライン完了 (session {session_number})"
        color = 0x2ECC71
    else:
        title = f"⚠️ パイプライン完了 ({fail_count}件失敗) (session {session_number})"
        color = 0xF39C12

    _send_webhook(
        {
            "title": title,
            "description": (
                "\n".join(lines) + f"\n\n**合計所要時間:** {total_elapsed:.0f}秒"
                f" ({success_count}成功 / {fail_count}失敗)"
            ),
            "color": color,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
