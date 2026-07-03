"""実行中の発言品質分析パイプラインを監視し、Discord に経過報告を送る。

ホストから直接実行する版。DBにはdocker composeのポート経由で接続。

使い方:
  python3 monitor.py
"""

import os
import time

import httpx
import psycopg2

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]  # 必須: Webhook URLはコードに書かない
# docker compose の db サービスはホスト側 5433 にマッピング
DB_URL = os.environ["DATABASE_URL"]  # 必須: 接続情報はコードに書かない
SESSION_NUMBER = 213
INTERVAL_SEC = 1800  # 30分


def send_discord(embed: dict) -> None:
    try:
        resp = httpx.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10.0)
        resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] Discord送信失敗: {e}")


def get_progress() -> tuple[int, int]:
    conn = psycopg2.connect(DB_URL)
    try:
        cur = conn.cursor()
        # session id
        cur.execute(
            "SELECT id FROM diet_sessions WHERE session_number = %s",
            (SESSION_NUMBER,),
        )
        row = cur.fetchone()
        if not row:
            return 0, 0
        session_id = row[0]

        # analyzed
        cur.execute(
            "SELECT COUNT(*) FROM speech_quality_scores WHERE session_id = %s",
            (session_id,),
        )
        analyzed = cur.fetchone()[0]

        # total (same filter as pipeline)
        cur.execute(
            """
            SELECT COUNT(*) FROM speeches s
            WHERE s.session_id = %s
              AND s.speech_chars >= 200
              AND s.member_id IS NOT NULL
              AND s.member_id NOT IN (
                  SELECT id FROM members WHERE role_category IN ('cabinet', 'chair')
              )
            """,
            (session_id,),
        )
        total = cur.fetchone()[0]
        return analyzed, total
    finally:
        conn.close()


def main():
    print(f"監視開始: session={SESSION_NUMBER}, interval={INTERVAL_SEC}s")

    prev_analyzed = None
    start_time = time.time()
    first_analyzed = None

    # 初回の進捗取得
    analyzed, total = get_progress()
    first_analyzed = analyzed
    pct = analyzed / total * 100 if total > 0 else 0

    send_discord(
        {
            "title": "🔬 発言品質分析の監視を開始しました",
            "description": (
                f"**会期:** {SESSION_NUMBER}\n"
                f"**現在の進捗:** {analyzed:,}/{total:,}件 ({pct:.1f}%)"
            ),
            "color": 0x3498DB,
        }
    )
    print(f"初回通知送信: {analyzed:,}/{total:,} ({pct:.1f}%)")
    prev_analyzed = analyzed

    while True:
        time.sleep(INTERVAL_SEC)

        analyzed, total = get_progress()
        if total == 0:
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
        send_discord({"title": f"🔬 発言品質分析 {pct:.1f}%", "description": msg, "color": 0x9B59B6})

        if analyzed >= total:
            send_discord(
                {
                    "title": "🎉 発言品質分析が完了しました",
                    "description": (
                        f"**会期:** {SESSION_NUMBER}\n"
                        f"**分析結果:** {analyzed:,}/{total:,}件\n"
                        f"**監視時間:** {elapsed / 3600:.1f}時間"
                    ),
                    "color": 0x2ECC71,
                }
            )
            print("完了を検出。監視終了。")
            break


if __name__ == "__main__":
    main()
