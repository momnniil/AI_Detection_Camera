# ============================================================
#  modules/ui.py  ─ 畫面 UI 繪製
# ============================================================
import cv2

from config import BAD_POSTURE_WARN_SEC, SITTING_LIMIT_MIN


def draw_ui(frame, state: dict) -> None:
    h, w = frame.shape[:2]
    pad = int(0.002 * w)
    box_w = int(0.32 * w)
    box_h = int(0.53 * h)  # 加高容納視距與疲勞資訊
    dis_x = int(0.01 * w)
    dis_y = int(0.06 * h)

    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale_large = w / 1920 * 2
    font_scale_med = w / 1920 * 1
    font_scale_small = w / 1920 * 0.9
    thickness_large = max(3, int(w / 1920 * 2))
    thickness_med = max(2, int(w / 1920 * 1))
    thickness_small = max(2, int(w / 1920 * 1))

    _, lh_large = cv2.getTextSize("A", font, font_scale_large, thickness_large)[:2]
    _, lh_med = cv2.getTextSize("A", font, font_scale_med, thickness_med)[:2]
    _, lh_small = cv2.getTextSize("A", font, font_scale_small, thickness_small)[:2]

    cv2.rectangle(frame, (pad, pad), (pad + box_w, pad + box_h), (40, 40, 40), -1)
    cv2.rectangle(frame, (pad, pad), (pad + box_w, pad + box_h), (110, 110, 110), 1)

    x, y = pad + dis_x, pad + dis_y

    if not state["is_calibrated"]:
        cv2.putText(
            frame,
            "Sit straight & press [C]",
            (x, y),
            font,
            font_scale_med,
            (0, 255, 255),
            thickness_med,
        )
        return

    if state.get("is_standing", False):
        cv2.putText(
            frame,
            "STANDING - Paused",
            (x, y),
            font,
            font_scale_med,
            (255, 255, 0),
            thickness_med,
        )
        return

    if state.get("mask_detected", False):
        cv2.putText(
            frame,
            "MASK ON - Eye only",
            (x, y),
            font,
            font_scale_small,
            (200, 200, 0),
            thickness_small,
        )
        y += lh_small + int(h / 1080 * 6)

    # 主狀態
    cv2.putText(
        frame,
        state["status"],
        (x, y),
        font,
        font_scale_large,
        state["color"],
        thickness_large,
    )
    y += lh_large + int(h / 1080 * 4)

    # 問題列表
    for issue in state["issues"]:
        cv2.putText(
            frame,
            f"  ! {issue}",
            (x, y + lh_med),
            font,
            font_scale_med,
            (0, 165, 255),
            thickness_med,
        )
        y += lh_med * 3

    # 眼睛資訊
    gaze_sec = state.get("gaze_still_sec", 0.0)
    blink_rate = state.get("blink_rate_min", 0.0)
    dist_cm = state.get("distance_cm", -1.0)
    gaze_color = (0, 100, 255) if gaze_sec >= 15 else (160, 160, 160)
    blink_color = (0, 0, 255) if (0 < blink_rate < 8) else (160, 160, 160)
    dist_color = (0, 0, 255) if (0 < dist_cm < 40) else (160, 160, 160)

    # 固定行距：畫面高度的 4.5%，避免 lh_small 太小造成重疊
    line_gap = max(18, int(h * 0.045))
    eye_y0 = pad + int(0.19 * h)

    cv2.putText(
        frame,
        f"Gaze still: {gaze_sec:.0f}s",
        (x, eye_y0),
        font,
        font_scale_small,
        gaze_color,
        thickness_small,
    )
    cv2.putText(
        frame,
        f"Blink: {blink_rate:.0f}/min",
        (x, eye_y0 + line_gap),
        font,
        font_scale_small,
        blink_color,
        thickness_small,
    )

    dist_text = f"Dist: {dist_cm:.0f}cm" if dist_cm > 0 else "Dist: --"
    cv2.putText(
        frame,
        dist_text,
        (x, eye_y0 + line_gap * 2),
        font,
        font_scale_small,
        dist_color,
        thickness_small,
    )

    fatigue_score = state.get("fatigue_score", 0.0)
    fatigue_label = state.get("fatigue_label", "Fresh")
    fatigue_colors = {
        "Fresh": (0, 220, 0),
        "Mild": (0, 200, 255),
        "Tired": (0, 140, 255),
        "Exhausted": (0, 0, 255),
    }
    f_color = fatigue_colors.get(fatigue_label, (160, 160, 160))
    cv2.putText(
        frame,
        f"Fatigue: {fatigue_score:.0f}  [{fatigue_label}]",
        (x, eye_y0 + line_gap * 3),
        font,
        font_scale_small,
        f_color,
        thickness_small,
    )

    # 高度數值（緊接在眼睛四行之後）
    cv2.putText(
        frame,
        f"Height {state['curr_Y']:.4f} (base {state['base_Y']:.4f})",
        (x, eye_y0 + line_gap * 4),
        font,
        font_scale_small,
        (180, 180, 180),
        thickness_small,
    )

    # 不良姿勢進度條
    if state["bad_elapsed"] > 0:
        ratio = min(state["bad_elapsed"] / BAD_POSTURE_WARN_SEC, 1.0)
        bar_full = box_w - int(h / 1080 * 28)
        bar_fill = int(ratio * bar_full)
        bar_y = eye_y0 + line_gap * 5
        cv2.rectangle(frame, (x, bar_y), (x + bar_full, bar_y + 10), (80, 80, 80), -1)
        cv2.rectangle(frame, (x, bar_y), (x + bar_fill, bar_y + 10), (0, 165, 255), -1)
        cv2.putText(
            frame,
            f"Bad: {state['bad_elapsed']:.0f}s / {BAD_POSTURE_WARN_SEC}s",
            (x, bar_y + line_gap),
            font,
            font_scale_small,
            (0, 165, 255),
            thickness_small,
        )

    # 久坐 & 好姿勢比例
    sit_color = (
        (0, 0, 255) if state["sitting_min"] >= SITTING_LIMIT_MIN else (200, 200, 200)
    )
    bottom_y = eye_y0 + line_gap * 7
    cv2.putText(
        frame,
        f"Sitting: {state['sitting_min']} min",
        (x, bottom_y),
        font,
        font_scale_med,
        sit_color,
        thickness_med,
    )
    cv2.putText(
        frame,
        f"Good rate: {state['good_pct']:.0f}%",
        (x + int(0.15 * w), bottom_y),
        font,
        font_scale_med,
        (0, 220, 0),
        thickness_med,
    )
