"""実行中の発言品質分析パイプラインを監視し、Discord に経過報告を送る。

使い方:
  docker compose exec backend python monitor_speech_quality.py
  # または
  docker compose exec -d backend python monitor_speech_quality.py  (バックグラウンド)
"""

import os
import sys
import time

import httpx
from sqlalchemy import func

# app パッケージを読める前提
from app.database import SessionLocal
from app.models.member import Member
from app.models.session import DietSession
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
SESSION_NUMBER = int(os.environ.get("MONITOR_SESSION", "213"))
INTERVAL_SEC = int(os.environ.get("MONITOR_INTERVAL", "300"))  # 5分ごと


def send_discord(embed: dict) -> None:
    if not WEBHOOK_URL:
        print("[WARN] DISCORD_WEBHOOK_URL is not set, skipping notification")
        return
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(WEBHOOK_URL, json={"embeds": [embed]})
            resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] Discord送信失敗: {e}")


def get_progress() -> tuple[int, int]:
    """(analyzed, total) を返す。"""
    db = SessionLocal()
    try:
        session = db.query(DietSession).filter_by(session_number=SESSION_NUMBER).first()
        if not session:
            return 0, 0

        analyzed = (
            db.query(func.count(SpeechQualityScore.id))
            .filter(SpeechQualityScore.session_id == session.id)
            .scalar()
        )

        skip_members = (
            db.query(Member.id)
            .filter(Member.role_category.in_(["cabinet", "chair"]))
            .subquery()
        )
        total = (
            db.query(func.count(Speech.id))
            .filter(
                Speech.session_id == session.id,
                Speech.speech_chars >= 200,
                Speech.member_id.isnot(None),
                ~Speech.member_id.in_(db.query(skip_members)),
            )
            .scalar()
        )
        return analyzed, total
    finally:
        db.close()


def main():
    print(f"監視開始: session={SESSION_NUMBER}, interval={INTERVAL_SEC}s")

    prev_analyzed = None
    start_time = time.time()
    first_analyzed = None

    while True:
        analyzed, total = get_progress()

        if first_analyzed is None:
            first_analyzed = analyzed

        if total == 0:
            print("対象発言が見つかりません。60秒後に再試行...")
            time.sleep(60)
            continue

        pct = analyzed / total * 100
        elapsed = time.time() - start_time
        new_since_start = analyzed - first_analyzed
        speed = new_since_start / elapsed if elapsed > 0 and new_since_start > 0 else 0
        remaining = total - analyzed
        eta_hours = remaining / speed / 3600 if speed > 0 else 0

        delta = analyzed - prev_analyzed if prev_analyzed is not None else 0
        prev_analyzed = analyzed

        msg = (
            f"**進捗:** {analyzed:,}/{total:,}件 ({pct:.1f}%)\n"
            f"**前回からの増分:** +{delta:,}件\n"
            f"**速度:** {speed:.1f} 件/秒\n"
            f"**残り:** {remaining:,}件 (約{eta_hours:.1f}時間)"
        )

        print(f"[{pct:.1f}%] {analyzed:,}/{total:,} (+{delta:,}), {speed:.1f}/s, ETA {eta_hours:.1f}h")

        send_discord(
            {
                "title": f"🔬 発言品質分析 {pct:.1f}%",
                "description": msg,
                "color": 0x9B59B6,
            }
        )

        # 完了チェック
        if analyzed >= total:
            total_h = elapsed / 3600
            send_discord(
                {
                    "title": "🎉 発言品質分析が完了しました",
                    "description": (
                        f"**会期:** {SESSION_NUMBER}\n"
                        f"**分析結果:** {analyzed:,}/{total:,}件\n"
                        f"**監視時間:** {total_h:.1f}時間"
                    ),
                    "color": 0x2ECC71,
                }
            )
            print("完了を検出。監視終了。")
            break

        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
