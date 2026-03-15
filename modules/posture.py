# ============================================================
#  modules/posture.py
# ============================================================
import numpy as np

from config import (STAND_SHOULDER_Y_RATIO, THRESHOLD_BODY_TILT,
                    THRESHOLD_HEAD_DROP, THRESHOLD_HUNCHING)


def calc_angle(a, b, c) -> float:
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cos_val = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return float(np.degrees(np.arccos(np.clip(cos_val, -1.0, 1.0))))


def is_standing(lm) -> bool:
    shoulder_y = (lm[11].y + lm[12].y) / 2
    return shoulder_y < STAND_SHOULDER_Y_RATIO


def calibrate(lm) -> dict:
    nose = [lm[0].x, lm[0].y]
    l_ear = [lm[7].x, lm[7].y]
    l_shoulder = [lm[11].x, lm[11].y]
    return {
        "Y": (lm[11].y + lm[12].y) / 2 - (lm[9].y + lm[10].y) / 2,
        "neck_angle": calc_angle(nose, l_ear, l_shoulder),
        "shoulder_diff": abs(lm[11].y - lm[12].y),
    }


def analyze_posture(lm, base: dict):
    issues = []

    m_y = (lm[9].y + lm[10].y) / 2
    s_y = (lm[11].y + lm[12].y) / 2
    curr_Y = s_y - m_y
    if (base["Y"] - curr_Y) > THRESHOLD_HEAD_DROP:
        issues.append("Forward/Head Drop")

    nose = [lm[0].x, lm[0].y]
    l_ear = [lm[7].x, lm[7].y]
    l_shoulder = [lm[11].x, lm[11].y]
    neck_angle = calc_angle(nose, l_ear, l_shoulder)
    if (base["neck_angle"] - neck_angle) > THRESHOLD_HUNCHING:
        issues.append("Hunching")

    shoulder_diff = abs(lm[11].y - lm[12].y)
    if (shoulder_diff - base["shoulder_diff"]) > THRESHOLD_BODY_TILT:
        issues.append("Body Tilt")

    good = len(issues) == 0
    status = "GOOD POSTURE" if good else "BAD POSTURE"
    color = (0, 200, 0) if good else (0, 0, 255)
    return status, issues, color, curr_Y, neck_angle, shoulder_diff
