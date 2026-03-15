import math
import time
import numpy as np
from config import (BLINK_CONSEC_FRAMES, BLINK_EAR_THRESH, BLINK_RATE_WARN_MIN,
                    EYE_GAZE_MOVE_THRESH, EYE_GAZE_STILL_SEC)

# ============================================================
#  modules/eye_tracker.py
#  - MediaPipe Iris 虹膜追蹤
#  - EAR / blink ratio 眨眼頻率
#  - Gaze Tracking 視線停留座標
#  - 虹膜幾何投影視距估算
#  - Cross-Modal Fusion 疲勞分數
# ============================================================

# ── FaceMesh 眼部 landmark 索引 ───────────────────────────────
LEFT_EYE = [
    362,
    382,
    381,
    380,
    374,
    373,
    390,
    249,
    263,
    466,
    388,
    387,
    386,
    385,
    384,
    398,
]
RIGHT_EYE = [
    33,
    7,
    163,
    144,
    145,
    153,
    154,
    155,
    133,
    173,
    157,
    158,
    159,
    160,
    161,
    246,
]

# 虹膜 landmark（refine_landmarks=True 才有）
# 左眼虹膜：468-472，右眼虹膜：473-477
# 各虹膜最左點與最右點用來量直徑
IRIS_LEFT_EDGE = (469, 471)  # 左虹膜左右端點
IRIS_RIGHT_EDGE = (474, 476)  # 右虹膜左右端點

# 虹膜實際直徑（mm），人眼平均值
IRIS_REAL_DIAMETER_MM = 11.7


# ── 工具函式 ──────────────────────────────────────────────────
def _poly_area(x, y) -> float:
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def _euclid(p1, p2) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def _blink_ratio(mesh_coords, right_idx, left_idx) -> float:
    """水平距離 / 垂直距離，值越大 = 眼睛越閉（EAR 的倒數形式）"""
    rh = _euclid(mesh_coords[right_idx[0]], mesh_coords[right_idx[8]])
    rv = _euclid(mesh_coords[right_idx[12]], mesh_coords[right_idx[4]])
    lh = _euclid(mesh_coords[left_idx[0]], mesh_coords[left_idx[8]])
    lv = _euclid(mesh_coords[left_idx[12]], mesh_coords[left_idx[4]])
    return ((rh / (rv + 1e-6)) + (lh / (lv + 1e-6))) / 2


def _get_gaze_point(face_lm) -> tuple:
    """用虹膜中心點取得注視座標（歸一化）"""
    try:
        # 468 = 左眼虹膜中心, 473 = 右眼虹膜中心
        lx, ly = face_lm[468].x, face_lm[468].y
        rx, ry = face_lm[473].x, face_lm[473].y
    except (IndexError, AttributeError):
        lx = (face_lm[33].x + face_lm[133].x) / 2
        ly = (face_lm[33].y + face_lm[133].y) / 2
        rx = (face_lm[362].x + face_lm[263].x) / 2
        ry = (face_lm[362].y + face_lm[263].y) / 2
    return (lx + rx) / 2, (ly + ry) / 2


def _estimate_distance(face_lm, img_w: int, focal_length_px: float) -> float:
    """
    虹膜幾何投影視距估算。
    原理：距離 = (虹膜實際直徑_mm × 焦距_px) / 虹膜像素寬度
    focal_length_px 預設用 img_w 當近似值（適合一般筆電鏡頭）。
    回傳距離（cm），失敗回傳 -1。
    """
    try:
        # 左虹膜直徑（像素）
        lx1 = face_lm[IRIS_LEFT_EDGE[0]].x * img_w
        lx2 = face_lm[IRIS_LEFT_EDGE[1]].x * img_w
        l_diam = abs(lx1 - lx2)

        # 右虹膜直徑（像素）
        rx1 = face_lm[IRIS_RIGHT_EDGE[0]].x * img_w
        rx2 = face_lm[IRIS_RIGHT_EDGE[1]].x * img_w
        r_diam = abs(rx1 - rx2)

        avg_diam_px = (l_diam + r_diam) / 2
        if avg_diam_px < 1:
            return -1.0

        # 相似三角形：dist(mm) = real_diam * focal / pixel_diam
        dist_mm = (IRIS_REAL_DIAMETER_MM * focal_length_px) / avg_diam_px
        return dist_mm / 10.0  # 轉成 cm
    except (IndexError, AttributeError):
        return -1.0


def _to_coords(face_lm, indices, img_w, img_h):
    return [(int(face_lm[i].x * img_w), int(face_lm[i].y * img_h)) for i in indices]


# ── Cross-Modal Fusion 疲勞評分 ───────────────────────────────
def compute_fatigue_score(
    blink_rate: float, gaze_still_sec: float, bad_posture_elapsed: float
) -> float:
    """
    多維度疲勞分數 0~100。
    - 眨眼率過低（< 8/min）→ 疲勞加分
    - 注視靜止太久（> 10s）→ 疲勞加分
    - 持續不良姿勢（> 10s）→ 疲勞加分
    """
    score = 0.0

    # 眨眼率維度（權重 40）
    # 正常 15-20/min，低於 8 視為疲勞
    if blink_rate > 0:
        blink_score = max(0.0, (8 - blink_rate) / 8) * 40
    else:
        blink_score = 0.0
    score += blink_score

    # 注視靜止維度（權重 35）
    # 超過 20s 滿分
    gaze_score = min(gaze_still_sec / 20.0, 1.0) * 35
    score += gaze_score

    # 姿勢維度（權重 25）
    # 超過 30s 滿分
    posture_score = min(bad_posture_elapsed / 30.0, 1.0) * 25
    score += posture_score

    return round(score, 1)


def fatigue_level(score: float) -> str:
    if score < 25:
        return "Fresh"
    elif score < 50:
        return "Mild"
    elif score < 75:
        return "Tired"
    else:
        return "Exhausted"


# ── EyeTracker ────────────────────────────────────────────────
class EyeTracker:
    def __init__(self):
        self._eye_area_ref = None
        self.reset()

    def reset(self):
        self._gaze_ref = None
        self._gaze_still_start = None
        self._gaze_warned = False

        self._blink_counter = 0
        self._blink_total = 0
        self._blink_window_start = time.time()
        self._blink_warned = False

        self.gaze_still_sec = 0.0
        self.blink_rate_min = 0.0
        self.eye_area = 0.0
        self.blink_ratio = 0.0
        self.distance_cm = -1.0  # 視距（cm），-1 = 無法估算
        self.fatigue_score = 0.0
        self.fatigue_label = "Fresh"

    def update(
        self,
        face_lm,
        img_w: int = 640,
        img_h: int = 480,
        bad_posture_elapsed: float = 0.0,
    ) -> list:
        """
        傳入 FaceMesh landmark list。
        bad_posture_elapsed: 從 main.py 傳入當前不良姿勢持續秒數，用於疲勞計算。
        回傳需要觸發的警告字串 list。
        """
        warnings = []
        now = time.time()

        # ── 1. 眨眼偵測（EAR / blink ratio）─────────────────
        try:
            mesh_coords = [
                (int(face_lm[i].x * img_w), int(face_lm[i].y * img_h))
                # FaceMesh with iris = 478 points
                for i in range(478)
            ]
            self.blink_ratio = _blink_ratio(mesh_coords, RIGHT_EYE, LEFT_EYE)

            r_coords = _to_coords(face_lm, RIGHT_EYE, img_w, img_h)
            l_coords = _to_coords(face_lm, LEFT_EYE, img_w, img_h)
            self.eye_area = (
                _poly_area(
                    np.array([p[0] for p in r_coords]),
                    np.array([p[1] for p in r_coords]),
                )
                + _poly_area(
                    np.array([p[0] for p in l_coords]),
                    np.array([p[1] for p in l_coords]),
                )
            ) / 2

            if self._eye_area_ref is None and self.eye_area > 10:
                self._eye_area_ref = self.eye_area

            if self.blink_ratio > BLINK_EAR_THRESH:
                self._blink_counter += 1
            else:
                if self._blink_counter >= BLINK_CONSEC_FRAMES:
                    self._blink_total += 1
                self._blink_counter = 0
        except Exception:
            pass

        # 每 60 秒結算眨眼率
        elapsed = now - self._blink_window_start
        if elapsed >= 60:
            self.blink_rate_min = self._blink_total / (elapsed / 60)
            if self.blink_rate_min < BLINK_RATE_WARN_MIN and not self._blink_warned:
                warnings.append("LOW_BLINK")
                self._blink_warned = True
            self._blink_window_start = now
            self._blink_total = 0
            self._blink_warned = False

        # ── 2. 虹膜幾何投影視距估算 ──────────────────────────
        focal_px = img_w  # 近似焦距（適合一般筆電 FOV ~60°）
        self.distance_cm = _estimate_distance(face_lm, img_w, focal_px)
        if 0 < self.distance_cm < 40:
            warnings.append("TOO_CLOSE")  # 距離螢幕小於 40cm 警告

        # ── 3. Gaze Tracking 注視停留 ────────────────────────
        try:
            gx, gy = _get_gaze_point(face_lm)
            if self._gaze_ref is None:
                self._gaze_ref = (gx, gy)
                self._gaze_still_start = now
            else:
                moved = (
                    math.hypot(gx - self._gaze_ref[0], gy - self._gaze_ref[1])
                    > EYE_GAZE_MOVE_THRESH
                )
                if moved:
                    self._gaze_ref = (gx, gy)
                    self._gaze_still_start = now
                    self._gaze_warned = False
                else:
                    self.gaze_still_sec = now - self._gaze_still_start
                    if (
                        self.gaze_still_sec >= EYE_GAZE_STILL_SEC
                        and not self._gaze_warned
                    ):
                        warnings.append("GAZE_FIXATION")
                        self._gaze_warned = True
        except Exception:
            pass

        # ── 4. Cross-Modal Fusion 疲勞評分 ───────────────────
        self.fatigue_score = compute_fatigue_score(
            self.blink_rate_min, self.gaze_still_sec, bad_posture_elapsed
        )
        self.fatigue_label = fatigue_level(self.fatigue_score)

        return warnings

    @property
    def gaze_info(self) -> dict:
        return {
            "gaze_still_sec": self.gaze_still_sec,
            "blink_rate_min": self.blink_rate_min,
            "eye_area": self.eye_area,
            "blink_ratio": self.blink_ratio,
            "distance_cm": self.distance_cm,
            "fatigue_score": self.fatigue_score,
            "fatigue_label": self.fatigue_label,
        }
