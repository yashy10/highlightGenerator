"""Auto-highlight service using YOLO player tracking and multi-signal scoring."""
import os
import logging
import cv2
import numpy as np
import torch
from collections import defaultdict

from ultralytics import YOLO
import supervision as sv

logger = logging.getLogger(__name__)

# Signal weights (sum to 1.0)
WEIGHTS = {
    "motion":      0.25,
    "accel":       0.20,
    "jump":        0.20,
    "size":        0.10,
    "centrality":  0.10,
    "persistence": 0.10,
    "ratio_var":   0.05,
}

# YOLO config
YOLO_MODEL = "yolo11n.pt"
YOLO_CONF = 0.3
YOLO_IOU = 0.5
PERSON_CLS = 0
BALL_CLS = 32

# Camera config
EMA_ALPHA = 0.04
CENTER_GRAVITY = 0.15
DEAD_ZONE_PCT = 0.09
DRIFT_BACK_RATE = 0.01

# Output
OUTPUT_W = 1080
OUTPUT_H = 1920

# Minimum frame presence
MIN_PRESENCE = 0.20

# Visual FX
SPOT_COLOR_HEX = "#FFD700"
SPOT_COLOR_BGR = (0, 215, 255)
SPOT_OPACITY = 0.6
TRACE_LENGTH = 15
TRACE_THICKNESS = 2
SPOT_THICKNESS = 2


def _detect_device() -> str:
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _euclidean(a, b) -> float:
    return float(np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))


def _normalize_scores(scores: dict) -> dict:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        return {tid: 0.5 for tid in scores}
    return {tid: (v - lo) / (hi - lo) for tid, v in scores.items()}


def _update_camera(
    smooth_cx: float,
    player_cx: float | None,
    frame_width: int,
    crop_width: int,
) -> float:
    frame_center = frame_width / 2.0
    if player_cx is None:
        smooth_cx += DRIFT_BACK_RATE * (frame_center - smooth_cx)
        return smooth_cx
    if abs(player_cx - smooth_cx) < crop_width * DEAD_ZONE_PCT:
        return smooth_cx
    gravity_target = player_cx * (1.0 - CENTER_GRAVITY) + frame_center * CENTER_GRAVITY
    smooth_cx = EMA_ALPHA * gravity_target + (1.0 - EMA_ALPHA) * smooth_cx
    return smooth_cx


def _draw_spotlight_fill(frame, xyxy, color_bgr=SPOT_COLOR_BGR, opacity=SPOT_OPACITY):
    x1, y1, x2, y2 = xyxy.astype(int)
    cx = (x1 + x2) // 2
    bottom = int(y2)
    half_w = max((x2 - x1) // 2, 1)
    half_h = max(half_w // 3, 8)
    overlay = frame.copy()
    cv2.ellipse(overlay, (cx, bottom), (half_w, half_h), 0, -45, 235, color_bgr, -1)
    cv2.addWeighted(overlay, opacity, frame, 1.0 - opacity, 0, dst=frame)


def _compute_target(all_dets, n_frames, frame_w):
    track_data = defaultdict(lambda: {
        "centroids": [],
        "areas": [],
        "y2_values": [],
        "ratios": [],
        "centrality_sum": 0.0,
        "frame_count": 0,
    })

    for det in all_dets:
        if det.tracker_id is None or len(det) == 0:
            continue
        persons = det[det.class_id == PERSON_CLS]
        if persons.tracker_id is None:
            continue
        for j in range(len(persons)):
            tid = persons.tracker_id[j]
            if tid is None:
                continue
            tid = int(tid)
            x1, y1, x2, y2 = persons.xyxy[j]
            cx = float((x1 + x2) / 2.0)
            cy = float((y1 + y2) / 2.0)
            area = float((x2 - x1) * (y2 - y1))
            bw = float(x2 - x1)
            bh = float(max(y2 - y1, 1.0))
            td = track_data[tid]
            td["centroids"].append((cx, cy))
            td["areas"].append(area)
            td["y2_values"].append(float(y2))
            td["ratios"].append(bw / bh)
            td["centrality_sum"] += 1.0 - abs(cx - frame_w / 2.0) / (frame_w / 2.0 + 1e-6)
            td["frame_count"] += 1

    if not track_data:
        raise RuntimeError("No persons detected in any frame.")

    valid_tids = {tid for tid, td in track_data.items()
                  if td["frame_count"] >= MIN_PRESENCE * n_frames}
    if not valid_tids:
        valid_tids = {tid for tid, td in track_data.items()
                      if td["frame_count"] >= 0.10 * n_frames}
    if not valid_tids:
        valid_tids = {tid for tid, td in track_data.items()
                      if td["frame_count"] >= 0.05 * n_frames}
    if not valid_tids:
        valid_tids = {max(track_data, key=lambda t: track_data[t]["frame_count"])}

    raw_motion, raw_accel, raw_jump = {}, {}, {}
    raw_size, raw_central, raw_persist, raw_ratio_var = {}, {}, {}, {}

    for tid in valid_tids:
        td = track_data[tid]
        centroids = td["centroids"]
        n_pts = len(centroids)

        total_dist = sum(_euclidean(centroids[i], centroids[i - 1]) for i in range(1, n_pts))
        raw_motion[tid] = total_dist

        speeds = [_euclidean(centroids[i], centroids[i - 1]) for i in range(1, n_pts)]
        raw_accel[tid] = sum(abs(speeds[i] - speeds[i - 1]) for i in range(1, len(speeds)))

        y2s = td["y2_values"]
        raw_jump[tid] = sum(max(y2s[i - 1] - y2s[i], 0) for i in range(1, len(y2s)))

        raw_size[tid] = float(np.mean(td["areas"]))
        raw_central[tid] = td["centrality_sum"] / max(td["frame_count"], 1)
        raw_persist[tid] = td["frame_count"]
        raw_ratio_var[tid] = float(np.var(td["ratios"])) if len(td["ratios"]) > 1 else 0.0

    norm = {
        "motion": _normalize_scores(raw_motion),
        "accel": _normalize_scores(raw_accel),
        "jump": _normalize_scores(raw_jump),
        "size": _normalize_scores(raw_size),
        "centrality": _normalize_scores(raw_central),
        "persistence": _normalize_scores(raw_persist),
        "ratio_var": _normalize_scores(raw_ratio_var),
    }

    final_scores = {}
    signal_table = {}
    for tid in valid_tids:
        per_signal = {}
        total = 0.0
        for sig_name, weight in WEIGHTS.items():
            val = norm[sig_name].get(tid, 0.0)
            per_signal[sig_name] = val
            total += weight * val
        final_scores[tid] = total
        signal_table[tid] = per_signal

    target_id = max(final_scores, key=final_scores.get)
    return int(target_id), final_scores, signal_table


class AutoHighlightService:
    """Processes a video using YOLO tracking and multi-signal scoring to generate a highlight."""

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            logger.info(f"Loading YOLO model: {YOLO_MODEL}")
            self._model = YOLO(YOLO_MODEL)
        return self._model

    def process_video(
        self,
        video_path: str,
        output_path: str,
        progress_callback=None,
    ) -> dict:
        """
        Process a video to generate a player highlight.

        Args:
            video_path: Path to input video
            output_path: Path for output highlight video
            progress_callback: Optional callable(phase, percent) for progress updates

        Returns:
            dict with target_id, scores, signal_table, duration, frames
        """
        device = _detect_device()
        model = self._get_model()

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        n_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        crop_h = frame_h
        crop_w = int(frame_h * 9.0 / 16.0 * 1.5)
        if crop_w > frame_w:
            crop_w = frame_w
            crop_h = int(frame_w * 16.0 / 9.0)

        logger.info(f"Video: {frame_w}x{frame_h} @ {fps:.1f}fps, {n_total} frames")

        # Phase A: YOLO Tracking
        if progress_callback:
            progress_callback("tracking", 0)

        all_dets = []
        n_tracked = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            results = model.track(
                frame, persist=True, device=device,
                verbose=False, conf=YOLO_CONF, iou=YOLO_IOU,
            )
            all_dets.append(sv.Detections.from_ultralytics(results[0]))
            n_tracked += 1
            if progress_callback and n_tracked % 20 == 0:
                pct = int(n_tracked / max(n_total, 1) * 100)
                progress_callback("tracking", pct)

        cap.release()
        logger.info(f"Phase A complete: tracked {n_tracked} frames")

        if progress_callback:
            progress_callback("tracking", 100)

        # Phase B: Multi-Signal Scoring
        if progress_callback:
            progress_callback("scoring", 0)

        target_id, final_scores, signal_table = _compute_target(all_dets, n_tracked, frame_w)
        logger.info(f"Phase B complete: target player ID {target_id}, score {final_scores[target_id]:.3f}")

        if progress_callback:
            progress_callback("scoring", 100)

        # Phase C: Rendering
        if progress_callback:
            progress_callback("rendering", 0)

        cap = cv2.VideoCapture(video_path)

        ellipse_ann = sv.EllipseAnnotator(
            color=sv.Color.from_hex(SPOT_COLOR_HEX),
            thickness=SPOT_THICKNESS,
            start_angle=-45,
            end_angle=235,
        )
        trace_ann = sv.TraceAnnotator(
            color=sv.Color.WHITE,
            thickness=TRACE_THICKNESS,
            trace_length=TRACE_LENGTH,
        )

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (OUTPUT_W, OUTPUT_H))

        if not writer.isOpened():
            cap.release()
            raise RuntimeError("Failed to create video writer")

        # Initialize camera position
        smooth_cx = float(frame_w / 2.0)
        for early_det in all_dets[:30]:
            if early_det.tracker_id is not None and len(early_det) > 0:
                mask = (early_det.tracker_id == target_id) & (early_det.class_id == PERSON_CLS)
                t_dets = early_det[mask]
                if len(t_dets) > 0:
                    box = t_dets.xyxy[0]
                    smooth_cx = float((box[0] + box[2]) / 2.0)
                    break

        frames_out = 0
        for idx in range(n_tracked):
            ok, frame = cap.read()
            if not ok:
                break

            det = all_dets[idx]
            player_cx = None
            target_box = None

            if det.tracker_id is not None and len(det) > 0:
                mask = (det.tracker_id == target_id) & (det.class_id == PERSON_CLS)
                t_dets = det[mask]
                if len(t_dets) > 0:
                    target_box = t_dets.xyxy[0]
                    player_cx = float((target_box[0] + target_box[2]) / 2.0)

            smooth_cx = _update_camera(smooth_cx, player_cx, frame_w, crop_w)

            half = crop_w / 2.0
            clamped_cx = float(np.clip(smooth_cx, half, frame_w - half))
            x1 = int(clamped_cx - half)
            x1 = max(0, min(x1, frame_w - crop_w))
            x2 = x1 + crop_w
            y1 = 0
            y2 = crop_h

            vis = frame.copy()
            if target_box is not None:
                _draw_spotlight_fill(vis, target_box)
            if target_box is not None and det.tracker_id is not None:
                t_mask = (det.tracker_id == target_id) & (det.class_id == PERSON_CLS)
                vis = ellipse_ann.annotate(scene=vis, detections=det[t_mask])

            ball_dets = det[det.class_id == BALL_CLS]
            if len(ball_dets) > 0:
                vis = trace_ann.annotate(scene=vis, detections=ball_dets)

            cropped = vis[y1:y2, x1:x2]
            output_frame = cv2.resize(cropped, (OUTPUT_W, OUTPUT_H), interpolation=cv2.INTER_LINEAR)
            writer.write(output_frame)
            frames_out += 1

            if progress_callback and frames_out % 20 == 0:
                pct = int(frames_out / max(n_tracked, 1) * 100)
                progress_callback("rendering", pct)

        writer.release()
        cap.release()

        if progress_callback:
            progress_callback("rendering", 100)

        duration = frames_out / fps if fps > 0 else 0
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024) if os.path.isfile(output_path) else 0

        logger.info(f"Phase C complete: {frames_out} frames, {duration:.1f}s, {file_size_mb:.1f}MB")

        return {
            "target_id": target_id,
            "score": final_scores[target_id],
            "signal_table": {str(k): v for k, v in signal_table.get(target_id, {}).items()},
            "all_scores": {str(k): v for k, v in final_scores.items()},
            "duration": duration,
            "frames": frames_out,
            "fps": fps,
            "resolution": f"{OUTPUT_W}x{OUTPUT_H}",
            "file_size_mb": round(file_size_mb, 1),
        }


_service = None


def get_auto_highlight_service() -> AutoHighlightService:
    global _service
    if _service is None:
        _service = AutoHighlightService()
    return _service
