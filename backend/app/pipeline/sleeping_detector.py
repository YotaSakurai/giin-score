"""居眠り検出パイプライン

国会中継動画からフレームを抽出し、議員の居眠りを検出する。

検出パターン:
  1. head_forward  — 頭部が前方に傾いている（うつむき居眠り）
  2. head_backward — 頭部が後方に傾いている（仰向け居眠り）

判定条件（全て満たす場合のみ候補に）:
  - 頭部傾斜角度が閾値を超えている
  - その状態が MIN_DURATION_SEC 以上持続している
  - その間の体の動きが少ない

使用例:
  python -m app.pipeline.runner --pipeline sleeping --session 215
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

# --- 設定 ---
FRAME_INTERVAL_SEC = float(os.getenv("SLEEPING_FRAME_INTERVAL", "5"))
MIN_DURATION_SEC = float(os.getenv("SLEEPING_MIN_DURATION", "60"))
FORWARD_ANGLE_THRESHOLD = float(os.getenv("SLEEPING_FORWARD_ANGLE", "30"))
BACKWARD_ANGLE_THRESHOLD = float(os.getenv("SLEEPING_BACKWARD_ANGLE", "25"))
CONFIDENCE_THRESHOLD = float(os.getenv("SLEEPING_CONFIDENCE_THRESHOLD", "0.6"))
EVIDENCE_DIR = os.getenv("SLEEPING_EVIDENCE_DIR", "/data/sleeping_evidence")
CLIP_MARGIN_SEC = float(os.getenv("SLEEPING_CLIP_MARGIN", "30"))
MOTION_THRESHOLD = float(os.getenv("SLEEPING_MOTION_THRESHOLD", "5.0"))


def detect_sleeping_in_video(
    db: Session,
    video_path: str,
    video_url: str,
    session_id: int,
    meeting_name: str | None = None,
    video_date: datetime | None = None,
) -> int:
    """1本の動画ファイルから居眠りを検出し、DBに保存する。

    Returns:
        検出された居眠り候補の数
    """
    import cv2

    from app.models.sleeping_detection import SleepingDetection

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        return 0

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_total = total_frames / fps if fps > 0 else 0
    frame_step = int(fps * FRAME_INTERVAL_SEC) if fps > 0 else 150

    logger.info(
        f"Processing video: {video_path} "
        f"(fps={fps:.1f}, duration={duration_total:.0f}s, "
        f"sampling every {FRAME_INTERVAL_SEC}s)"
    )

    # MediaPipe Face Mesh 初期化
    import mediapipe as mp

    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=20,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    # 各検出された顔の追跡状態
    # key: (顔の位置ハッシュ), value: 追跡情報
    trackers: dict[int, _FaceTracker] = {}
    detections: list[dict] = []
    frame_idx = 0

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_idx / fps if fps > 0 else 0
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            h, w = frame.shape[:2]
            active_tracker_ids = set()

            for face_landmarks in results.multi_face_landmarks:
                # 頭部姿勢推定
                pitch, yaw, roll = _estimate_head_pose(face_landmarks, w, h)
                face_center = _get_face_center(face_landmarks, w, h)

                # 最も近いトラッカーにマッチング
                tracker_id = _match_tracker(trackers, face_center, w)
                active_tracker_ids.add(tracker_id)

                if tracker_id not in trackers:
                    trackers[tracker_id] = _FaceTracker(
                        tracker_id, face_center, current_time
                    )

                tracker = trackers[tracker_id]
                tracker.update(
                    pitch=pitch,
                    yaw=yaw,
                    roll=roll,
                    center=face_center,
                    time_sec=current_time,
                    frame=frame.copy(),
                )

                # 居眠り判定
                sleeping_info = tracker.check_sleeping()
                if sleeping_info:
                    detections.append(sleeping_info)
                    tracker.reset()

        frame_idx += frame_step

    face_mesh.close()
    cap.release()

    # 証拠保存 & DB登録
    evidence_dir = Path(EVIDENCE_DIR)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for det in detections:
        # スクリーンショット保存
        screenshot_filename = (
            f"sleep_{session_id}_{det['start_time']:.0f}_{det['tracker_id']}.jpg"
        )
        screenshot_path = evidence_dir / screenshot_filename
        if det.get("peak_frame") is not None:
            cv2.imwrite(str(screenshot_path), det["peak_frame"])
        else:
            screenshot_path = None

        # 動画クリップ切り出し
        clip_path = None
        if video_path:
            clip_filename = (
                f"clip_{session_id}_{det['start_time']:.0f}_{det['tracker_id']}.mp4"
            )
            clip_full_path = evidence_dir / clip_filename
            clip_start = max(0, det["start_time"] - CLIP_MARGIN_SEC)
            clip_duration = det["duration"] + CLIP_MARGIN_SEC * 2
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-ss",
                        str(clip_start),
                        "-i",
                        video_path,
                        "-t",
                        str(clip_duration),
                        "-c:v",
                        "libx264",
                        "-preset",
                        "fast",
                        "-crf",
                        "28",
                        "-an",
                        str(clip_full_path),
                    ],
                    capture_output=True,
                    timeout=120,
                    check=False,
                )
                if clip_full_path.exists():
                    clip_path = str(clip_full_path)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("ffmpeg clip extraction failed")

        detection = SleepingDetection(
            session_id=session_id,
            video_url=video_url,
            video_date=video_date,
            meeting_name=meeting_name,
            start_time_sec=det["start_time"],
            end_time_sec=det["end_time"],
            duration_sec=det["duration"],
            detection_type=det["type"],
            confidence=det["confidence"],
            head_angle_avg=det.get("angle_avg"),
            screenshot_path=str(screenshot_path) if screenshot_path else None,
            clip_path=clip_path,
            review_status="pending",
        )
        db.add(detection)
        count += 1

    db.commit()
    logger.info(f"Detected {count} sleeping candidates in {video_path}")
    return count


class _FaceTracker:
    """個々の顔を時系列で追跡し、居眠り状態を判定する。"""

    def __init__(self, tracker_id: int, center: tuple[int, int], start_time: float):
        self.tracker_id = tracker_id
        self.center = center
        self.start_time = start_time

        # 居眠り候補の状態
        self.sleeping_start: float | None = None
        self.sleeping_type: str | None = None
        self.pitch_history: list[float] = []
        self.motion_history: list[float] = []
        self.peak_frame: np.ndarray | None = None
        self.peak_angle: float = 0.0

        # 前フレーム情報
        self.prev_center: tuple[int, int] = center
        self.prev_time: float = start_time

    def update(
        self,
        pitch: float,
        yaw: float,
        roll: float,
        center: tuple[int, int],
        time_sec: float,
        frame: np.ndarray,
    ):
        """新しいフレームの情報で更新する。"""
        # 動き量の計算
        dx = center[0] - self.prev_center[0]
        dy = center[1] - self.prev_center[1]
        motion = (dx**2 + dy**2) ** 0.5
        self.motion_history.append(motion)

        # 居眠りパターン判定
        is_forward = pitch > FORWARD_ANGLE_THRESHOLD  # 前傾（うつむき）
        is_backward = pitch < -BACKWARD_ANGLE_THRESHOLD  # 後傾（仰向け）

        if is_forward or is_backward:
            current_type = "head_forward" if is_forward else "head_backward"

            if self.sleeping_start is None or self.sleeping_type != current_type:
                # 新しい居眠り候補開始
                self.sleeping_start = time_sec
                self.sleeping_type = current_type
                self.pitch_history = [pitch]
                self.motion_history = [motion]
                self.peak_angle = abs(pitch)
                self.peak_frame = frame.copy()
            else:
                # 継続
                self.pitch_history.append(pitch)
                if abs(pitch) > self.peak_angle:
                    self.peak_angle = abs(pitch)
                    self.peak_frame = frame.copy()
        else:
            # 居眠り状態が解除された
            if self.sleeping_start is not None:
                self._finalize(time_sec)

        self.prev_center = center
        self.prev_time = time_sec
        self.center = center

    def check_sleeping(self) -> dict | None:
        """現在蓄積されている情報で居眠り判定を行う。"""
        if self.sleeping_start is None:
            return None

        duration = self.prev_time - self.sleeping_start
        if duration < MIN_DURATION_SEC:
            return None

        # 動きが多い場合は居眠りではない（資料をめくっている等）
        avg_motion = (
            sum(self.motion_history) / len(self.motion_history)
            if self.motion_history
            else 0
        )
        if avg_motion > MOTION_THRESHOLD:
            return None

        # 信頼度計算
        confidence = self._compute_confidence(duration, avg_motion)
        if confidence < CONFIDENCE_THRESHOLD:
            return None

        return {
            "tracker_id": self.tracker_id,
            "start_time": self.sleeping_start,
            "end_time": self.prev_time,
            "duration": duration,
            "type": self.sleeping_type,
            "confidence": round(confidence, 3),
            "angle_avg": round(
                sum(abs(p) for p in self.pitch_history) / len(self.pitch_history), 1
            )
            if self.pitch_history
            else None,
            "peak_frame": self.peak_frame,
        }

    def _finalize(self, end_time: float):
        """居眠り候補の追跡をリセットする。check_sleeping() で先に判定結果を取得すること。"""
        self.sleeping_start = None
        self.sleeping_type = None
        self.pitch_history = []
        self.motion_history = []
        self.peak_frame = None
        self.peak_angle = 0.0

    def reset(self):
        """検出済みとしてリセットする。"""
        self._finalize(self.prev_time)

    def _compute_confidence(self, duration: float, avg_motion: float) -> float:
        """居眠りの信頼度を算出する (0.0-1.0)。"""
        # 持続時間: 60秒で0.5, 180秒で0.8, 300秒以上で1.0
        duration_score = min(duration / 300, 1.0)

        # 角度の安定性: 角度の標準偏差が小さいほど高い
        if len(self.pitch_history) >= 2:
            mean = sum(self.pitch_history) / len(self.pitch_history)
            variance = sum((x - mean) ** 2 for x in self.pitch_history) / len(self.pitch_history)
            std = variance**0.5
            stability_score = max(0, 1.0 - std / 15.0)
        else:
            stability_score = 0.3

        # 動きの少なさ
        motion_score = max(0, 1.0 - avg_motion / MOTION_THRESHOLD)

        # 平均角度の大きさ: 大きいほど居眠りの可能性が高い
        avg_angle = (
            sum(abs(p) for p in self.pitch_history) / len(self.pitch_history)
            if self.pitch_history
            else 0
        )
        angle_threshold = (
            FORWARD_ANGLE_THRESHOLD
            if self.sleeping_type == "head_forward"
            else BACKWARD_ANGLE_THRESHOLD
        )
        angle_score = min((avg_angle - angle_threshold) / 20.0 + 0.5, 1.0)

        confidence = (
            duration_score * 0.3
            + stability_score * 0.25
            + motion_score * 0.25
            + angle_score * 0.2
        )
        return min(max(confidence, 0.0), 1.0)


def _estimate_head_pose(
    face_landmarks, img_w: int, img_h: int
) -> tuple[float, float, float]:
    """MediaPipe Face Meshのランドマークから頭部のpitch/yaw/rollを推定する。

    Returns:
        (pitch, yaw, roll) in degrees.
        pitch > 0: 下向き (前傾)
        pitch < 0: 上向き (後傾)
    """
    import cv2
    import numpy as np

    # 6点モデル (nose tip, chin, left/right eye corner, left/right mouth corner)
    landmarks_3d = np.array(
        [
            [0.0, 0.0, 0.0],  # Nose tip
            [0.0, -330.0, -65.0],  # Chin
            [-225.0, 170.0, -135.0],  # Left eye left corner
            [225.0, 170.0, -135.0],  # Right eye right corner
            [-150.0, -150.0, -125.0],  # Left mouth corner
            [150.0, -150.0, -125.0],  # Right mouth corner
        ],
        dtype=np.float64,
    )

    # MediaPipeのランドマークインデックス
    indices = [1, 152, 33, 263, 61, 291]
    landmarks_2d = np.array(
        [
            [
                face_landmarks.landmark[i].x * img_w,
                face_landmarks.landmark[i].y * img_h,
            ]
            for i in indices
        ],
        dtype=np.float64,
    )

    # カメラ行列
    focal_length = img_w
    camera_matrix = np.array(
        [
            [focal_length, 0, img_w / 2],
            [0, focal_length, img_h / 2],
            [0, 0, 1],
        ],
        dtype=np.float64,
    )
    dist_coeffs = np.zeros((4, 1))

    success, rotation_vec, translation_vec = cv2.solvePnP(
        landmarks_3d, landmarks_2d, camera_matrix, dist_coeffs
    )

    if not success:
        return 0.0, 0.0, 0.0

    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    angles, _, _, _, _, _ = cv2.RQDecomp3x3(rotation_mat)

    pitch = angles[0]  # + = 下向き, - = 上向き
    yaw = angles[1]
    roll = angles[2]

    return pitch, yaw, roll


def _get_face_center(
    face_landmarks, img_w: int, img_h: int
) -> tuple[int, int]:
    """顔の中心座標を取得する。"""
    nose = face_landmarks.landmark[1]
    return int(nose.x * img_w), int(nose.y * img_h)


def _match_tracker(
    trackers: dict[int, _FaceTracker],
    face_center: tuple[int, int],
    img_w: int,
) -> int:
    """最も近いトラッカーを見つける。距離が遠い場合は新しいIDを割り当てる。"""
    max_distance = img_w * 0.1  # 画像幅の10%以内

    best_id = None
    best_dist = float("inf")

    for tid, tracker in trackers.items():
        dx = face_center[0] - tracker.center[0]
        dy = face_center[1] - tracker.center[1]
        dist = (dx**2 + dy**2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best_id = tid

    if best_id is not None and best_dist < max_distance:
        return best_id

    # 新しいトラッカー
    return max(trackers.keys(), default=-1) + 1


def download_diet_video(video_url: str, output_dir: str | None = None) -> str | None:
    """国会中継動画をダウンロードする。

    衆議院TV / 参議院インターネット審議中継のURLに対応。
    yt-dlp を使用してダウンロードする。

    Returns:
        ダウンロードしたファイルのパス、失敗時はNone
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="diet_video_")

    output_path = os.path.join(output_dir, "%(title)s.%(ext)s")

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--no-playlist",
                "-f",
                "best[height<=720]",
                "-o",
                output_path,
                "--print",
                "after_move:filepath",
                video_url,
            ],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )

        if result.returncode != 0:
            logger.error(f"yt-dlp failed: {result.stderr}")
            return None

        filepath = result.stdout.strip().split("\n")[-1]
        if os.path.exists(filepath):
            logger.info(f"Downloaded: {filepath}")
            return filepath
        else:
            logger.error(f"Downloaded file not found: {filepath}")
            return None
    except subprocess.TimeoutExpired:
        logger.error("Video download timed out (600s)")
        return None
    except FileNotFoundError:
        logger.error("yt-dlp not found. Install with: pip install yt-dlp")
        return None


def detect_sleeping_for_session(db: Session, session_number: int) -> int:
    """会期の動画から居眠りを検出する。

    動画URLリストはDB内の会議データから取得するか、
    環境変数 SLEEPING_VIDEO_URLS で指定する。
    """
    from app.models.session import DietSession

    diet_session = (
        db.query(DietSession).filter_by(session_number=session_number).first()
    )
    if not diet_session:
        logger.error(f"Session {session_number} not found")
        return 0

    # 動画URLの取得
    video_urls = _get_video_urls(db, session_number)
    if not video_urls:
        logger.warning(f"No video URLs found for session {session_number}")
        return 0

    total_detections = 0

    for video_info in video_urls:
        video_url = video_info["url"]
        meeting_name = video_info.get("meeting_name")
        video_date = video_info.get("date")

        logger.info(f"Processing: {meeting_name or video_url}")

        # ダウンロード
        video_path = download_diet_video(video_url)
        if not video_path:
            logger.warning(f"Failed to download: {video_url}")
            continue

        try:
            count = detect_sleeping_in_video(
                db=db,
                video_path=video_path,
                video_url=video_url,
                session_id=diet_session.id,
                meeting_name=meeting_name,
                video_date=video_date,
            )
            total_detections += count
        finally:
            # ダウンロードファイルの削除
            try:
                os.unlink(video_path)
            except OSError:
                pass

    logger.info(
        f"Session {session_number}: {total_detections} sleeping candidates detected"
    )
    return total_detections


def _get_video_urls(
    db: Session, session_number: int
) -> list[dict]:
    """処理対象の動画URLリストを取得する。

    優先順位:
    1. 環境変数 SLEEPING_VIDEO_URLS (カンマ区切り)
    2. 将来的にはDB内の会議データから自動取得
    """
    env_urls = os.getenv("SLEEPING_VIDEO_URLS", "")
    if env_urls:
        return [{"url": url.strip()} for url in env_urls.split(",") if url.strip()]

    # 将来: 衆議院TV / 参議院中継 の動画URL一覧をスクレイピング
    logger.info(
        "No SLEEPING_VIDEO_URLS set. "
        "Set environment variable with comma-separated video URLs."
    )
    return []
