"""国会中継動画URL取得スクレイパー

衆議院インターネット審議中継（衆議院TV）と参議院インターネット審議中継から
動画URLを自動取得する。

衆議院TV:
  - URL: https://www.shugiintv.go.jp/jp/index.php?ex=VL&deli_id={id}
  - deli_id は連番整数。ページ内の m3u8 URL に日付が埋め込まれている
  - yt-dlp に ShugiinItvVodIE エクストラクタが内蔵されている

参議院TV:
  - URL: https://www.webtv.sangiin.go.jp/webtv/detail.php?sid={id}
  - sid は連番整数。<dl class="date"> 内に開会日・会議名がある
  - yt-dlp に SangiinIE エクストラクタが内蔵されている
"""

import logging
import re
import time
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.pipeline.utils import USER_AGENT

logger = logging.getLogger(__name__)

SHUGIINTV_BASE = "https://www.shugiintv.go.jp/jp/index.php?ex=VL&deli_id={deli_id}"
SANGIINTV_BASE = "https://www.webtv.sangiin.go.jp/webtv/detail.php?sid={sid}"

REQUEST_INTERVAL = 0.5

# 会期ごとの開始日（主要な最近の会期のみ）
# 開始日が不明な場合は外側でdate rangeを指定してスキャンする
SESSION_DATE_RANGES: dict[int, tuple[str, str]] = {
    215: ("2024-10-04", "2024-12-21"),
    216: ("2025-01-24", "2025-03-31"),
    217: ("2025-06-20", "2025-06-20"),
    218: ("2025-07-04", "2025-08-05"),
    219: ("2025-10-06", "2025-12-13"),
    220: ("2025-11-11", "2025-12-21"),
    221: ("2026-01-26", "2026-07-25"),
}


def get_video_urls_for_session(
    db: Session,
    session_number: int,
    chambers: list[str] | None = None,
) -> list[dict]:
    """会期に該当する動画URLを衆議院TV・参議院TVから取得する。

    Args:
        db: DBセッション
        session_number: 会期番号
        chambers: 対象院 (["shugiin", "sangiin"])。Noneなら両方

    Returns:
        [{"url": str, "meeting_name": str, "date": datetime, "chamber": str}, ...]
    """
    if chambers is None:
        chambers = ["shugiin", "sangiin"]

    date_range = _get_session_date_range(db, session_number)
    if not date_range:
        logger.error(f"Cannot determine date range for session {session_number}")
        return []

    start_date, end_date = date_range
    logger.info(
        f"Scanning videos for session {session_number}: "
        f"{start_date.isoformat()} ~ {end_date.isoformat()}"
    )

    results = []

    if "shugiin" in chambers:
        shugiin_videos = _scan_shugiintv(start_date, end_date)
        results.extend(shugiin_videos)
        logger.info(f"Shugiin TV: found {len(shugiin_videos)} videos")

    if "sangiin" in chambers:
        sangiin_videos = _scan_sangiintv(start_date, end_date)
        results.extend(sangiin_videos)
        logger.info(f"Sangiin TV: found {len(sangiin_videos)} videos")

    results.sort(key=lambda x: x.get("date") or datetime.min)
    return results


def _get_session_date_range(db: Session, session_number: int) -> tuple[date, date] | None:
    """会期の日付範囲を取得する。DB→ハードコード辞書の順で探す。"""
    from app.models.session import DietSession

    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if diet_session and diet_session.start_date and diet_session.end_date:
        return diet_session.start_date, diet_session.end_date

    if session_number in SESSION_DATE_RANGES:
        s, e = SESSION_DATE_RANGES[session_number]
        return date.fromisoformat(s), date.fromisoformat(e)

    return None


def _scan_shugiintv(
    start_date: date,
    end_date: date,
    batch_size: int = 50,
) -> list[dict]:
    """衆議院TVのdeli_idを連番スキャンして、日付範囲内の動画を収集する。"""
    # 最新の既知IDから逆方向にスキャンして開始IDを推定
    start_id = _estimate_shugiintv_start_id(start_date)
    end_id = start_id + 1000  # 1会期で最大1000本程度

    results = []
    consecutive_misses = 0
    max_consecutive_misses = 20

    logger.info(f"Shugiin TV: scanning deli_id {start_id}~{end_id}")

    with httpx.Client(
        timeout=15.0,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        for deli_id in range(start_id, end_id):
            time.sleep(REQUEST_INTERVAL)

            video_info = _fetch_shugiintv_info(client, deli_id)
            if video_info is None:
                consecutive_misses += 1
                if consecutive_misses >= max_consecutive_misses:
                    logger.info(
                        f"Shugiin TV: {max_consecutive_misses} consecutive misses "
                        f"at deli_id={deli_id}, stopping scan"
                    )
                    break
                continue

            consecutive_misses = 0
            video_date = video_info["date"]

            if video_date and video_date.date() < start_date:
                continue
            if video_date and video_date.date() > end_date:
                logger.info(
                    f"Shugiin TV: passed end_date at deli_id={deli_id} "
                    f"({video_date.date()}), stopping"
                )
                break

            results.append(
                {
                    "url": SHUGIINTV_BASE.format(deli_id=deli_id),
                    "meeting_name": video_info.get("meeting_name", ""),
                    "date": video_date,
                    "chamber": "shugiin",
                    "source_id": f"shugiin_{deli_id}",
                }
            )

    return results


def _fetch_shugiintv_info(client: httpx.Client, deli_id: int) -> dict | None:
    """衆議院TVの1ページからメタ情報を取得する。"""
    url = SHUGIINTV_BASE.format(deli_id=deli_id)
    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # m3u8 URLから日付抽出
        vod_input = soup.find("input", id="vtag_src_base_vod")
        if not vod_input or not vod_input.get("value"):
            return None

        m3u8_url = vod_input["value"]
        video_date = _parse_shugiintv_date(m3u8_url)

        # 会議名: ページ内テキストから取得
        meeting_name = ""
        for text in soup.stripped_strings:
            if len(text) > 3 and any(
                kw in text for kw in ["委員会", "本会議", "審査会", "調査会", "特別委"]
            ):
                meeting_name = re.sub(r"\s*[\(（].*?[\)）]$", "", text.strip())
                break

        return {
            "date": video_date,
            "meeting_name": meeting_name,
        }
    except (httpx.HTTPError, Exception) as e:
        logger.debug(f"Shugiin TV deli_id={deli_id}: {e}")
        return None


def _parse_shugiintv_date(m3u8_url: str) -> datetime | None:
    """m3u8 URLから日付を抽出する。
    例: .../2026/2026-0717-1300-00/playlist.m3u8 -> 2026-07-17 13:00
    """
    match = re.search(r"/(\d{4})-(\d{2})(\d{2})-(\d{2})(\d{2})", m3u8_url)
    if not match:
        return None
    y, m, d, h, mi = match.groups()
    try:
        return datetime(int(y), int(m), int(d), int(h), int(mi))
    except ValueError:
        return None


def _estimate_shugiintv_start_id(target_date: date) -> int:
    """目標日付に対応するdeli_idの開始推定値を返す。

    既知のアンカーポイントから線形補間で推定する。
    """
    # (date, deli_id) のアンカーポイント
    anchors = [
        (date(2025, 5, 21), 55800),
        (date(2025, 11, 26), 56000),
        (date(2026, 3, 5), 56100),
        (date(2026, 7, 17), 56386),
    ]

    if target_date <= anchors[0][0]:
        return anchors[0][1] - 200

    if target_date >= anchors[-1][0]:
        # 直近アンカーから外挿
        d1, id1 = anchors[-2]
        d2, id2 = anchors[-1]
        days_per_id = (d2 - d1).days / max(id2 - id1, 1)
        extra_days = (target_date - d2).days
        extra_ids = int(extra_days / days_per_id) if days_per_id > 0 else 50
        return id2 + extra_ids

    # 内挿
    for i in range(len(anchors) - 1):
        d1, id1 = anchors[i]
        d2, id2 = anchors[i + 1]
        if d1 <= target_date <= d2:
            ratio = (target_date - d1).days / max((d2 - d1).days, 1)
            estimated_id = int(id1 + ratio * (id2 - id1))
            return max(estimated_id - 50, id1)  # 余裕を持って少し前から

    return anchors[0][1]


def _scan_sangiintv(
    start_date: date,
    end_date: date,
) -> list[dict]:
    """参議院TVのsidを連番スキャンして、日付範囲内の動画を収集する。"""
    start_sid = _estimate_sangiintv_start_sid(start_date)
    end_sid = start_sid + 500

    results = []
    consecutive_misses = 0
    max_consecutive_misses = 20

    logger.info(f"Sangiin TV: scanning sid {start_sid}~{end_sid}")

    with httpx.Client(
        timeout=15.0,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        for sid in range(start_sid, end_sid):
            time.sleep(REQUEST_INTERVAL)

            video_info = _fetch_sangiintv_info(client, sid)
            if video_info is None:
                consecutive_misses += 1
                if consecutive_misses >= max_consecutive_misses:
                    logger.info(
                        f"Sangiin TV: {max_consecutive_misses} consecutive misses "
                        f"at sid={sid}, stopping scan"
                    )
                    break
                continue

            consecutive_misses = 0
            video_date = video_info["date"]

            if video_date and video_date < start_date:
                continue
            if video_date and video_date > end_date:
                logger.info(f"Sangiin TV: passed end_date at sid={sid} ({video_date}), stopping")
                break

            results.append(
                {
                    "url": SANGIINTV_BASE.format(sid=sid),
                    "meeting_name": video_info.get("meeting_name", ""),
                    "date": datetime.combine(video_date, datetime.min.time())
                    if video_date
                    else None,
                    "chamber": "sangiin",
                    "source_id": f"sangiin_{sid}",
                }
            )

    return results


def _fetch_sangiintv_info(client: httpx.Client, sid: int) -> dict | None:
    """参議院TVの1ページからメタ情報を取得する。"""
    url = SANGIINTV_BASE.format(sid=sid)
    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # <dl class="date"> から情報抽出
        info = {}
        for dl in soup.find_all("dl", class_="date"):
            dt = dl.find("dt")
            dd = dl.find("dd")
            if dt and dd:
                info[dt.get_text(strip=True)] = dd.get_text(strip=True)

        if not info.get("開会日"):
            return None

        video_date = _parse_japanese_date(info["開会日"])
        meeting_name = info.get("会議名", "")

        return {
            "date": video_date,
            "meeting_name": meeting_name,
        }
    except (httpx.HTTPError, Exception) as e:
        logger.debug(f"Sangiin TV sid={sid}: {e}")
        return None


def _parse_japanese_date(text: str) -> date | None:
    """'2026年7月17日' -> date(2026, 7, 17)"""
    match = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _estimate_sangiintv_start_sid(target_date: date) -> int:
    """目標日付に対応するsidの開始推定値を返す。"""
    anchors = [
        (date(2024, 5, 30), 8000),
        (date(2025, 3, 26), 8400),
        (date(2025, 10, 21), 8700),
        (date(2026, 5, 13), 9000),
    ]

    if target_date <= anchors[0][0]:
        return anchors[0][1] - 100

    if target_date >= anchors[-1][0]:
        d1, id1 = anchors[-2]
        d2, id2 = anchors[-1]
        days_per_id = (d2 - d1).days / max(id2 - id1, 1)
        extra_days = (target_date - d2).days
        extra_ids = int(extra_days / days_per_id) if days_per_id > 0 else 30
        return id2 + extra_ids

    for i in range(len(anchors) - 1):
        d1, id1 = anchors[i]
        d2, id2 = anchors[i + 1]
        if d1 <= target_date <= d2:
            ratio = (target_date - d1).days / max((d2 - d1).days, 1)
            estimated_id = int(id1 + ratio * (id2 - id1))
            return max(estimated_id - 30, id1)

    return anchors[0][1]
