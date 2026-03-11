import cv2
import mediapipe as mp
import numpy as np
import csv
import time
import threading
from datetime import datetime

# ============================================================
#  設定區（所有可調參數集中在這裡）
# ============================================================
CAMERA_INDEX        = 0
SAVE_INTERVAL_SEC   = 3
SITTING_LIMIT_MIN   = 40
BAD_POSTURE_WARN_SEC = 30   # 持續不良姿勢幾秒後警告

THRESHOLD_HEAD_DROP  = 0.04  # 低頭門檻（Y 掉落比例）
THRESHOLD_HUNCHING   = 15    # 駝背門檻（角度差，與校準時比）
THRESHOLD_BODY_TILT  = 0.02  # 歪斜門檻（肩膀高低差，與校準時比）

# ============================================================
#  MediaPipe 初始化
# ============================================================
mp_pose   = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# ============================================================
#  CSV 初始化
# ============================================================
today = datetime.now().strftime("%Y%m%d")
csv_file = open(f"posture_report_{today}.csv", "w", newline="", encoding="utf-8")
writer   = csv.writer(csv_file)
writer.writerow(["Time", "curr_Y", "neck_angle", "shoulder_diff", "Status", "Issues"])

# ============================================================
#  工具函式
# ============================================================
def calc_angle(a, b, c):
    """計算 a-b-c 三點夾角（度）"""
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc  = a - b, c - b
    cos_val = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return np.degrees(np.arccos(np.clip(cos_val, -1.0, 1.0)))

def show_popup_async(message):
    """在背景執行緒彈出提示，不凍結主程式"""
    def _popup():
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, "AI Posture Warning", 0x30)
    threading.Thread(target=_popup, daemon=True).start()

# ============================================================
#  姿勢分析（需傳入校準基準）
# ============================================================
def analyze_posture(lm, base):
    """
    base = {
        "Y"             : float,  # 校準時的嘴巴到肩膀高度差
        "neck_angle"    : float,  # 校準時的頸部角度
        "shoulder_diff" : float,  # 校準時的左右肩高低差
    }
    回傳 (status, issues, color, curr_Y, neck_angle, shoulder_diff)
    """
    issues = []

    # 指標 1：低頭 / 前傾
    m_y    = (lm[9].y  + lm[10].y) / 2
    s_y    = (lm[11].y + lm[12].y) / 2
    curr_Y = s_y - m_y
    if (base["Y"] - curr_Y) > THRESHOLD_HEAD_DROP:
        issues.append("Forward/Head Drop")

    # 指標 2：駝背（與校準角度比，角度掉太多 = 駝背）
    nose      = [lm[0].x,  lm[0].y]
    l_ear     = [lm[7].x,  lm[7].y]
    l_shoulder= [lm[11].x, lm[11].y]
    neck_angle = calc_angle(nose, l_ear, l_shoulder)
    if (base["neck_angle"] - neck_angle) > THRESHOLD_HUNCHING:
        issues.append("Hunching")

    # 指標 3：身體歪斜（與校準差值比）
    shoulder_diff = abs(lm[11].y - lm[12].y)
    if (shoulder_diff - base["shoulder_diff"]) > THRESHOLD_BODY_TILT:
        issues.append("Body Tilt")

    good   = len(issues) == 0
    status = "GOOD POSTURE" if good else "BAD POSTURE"
    color  = (0, 200, 0)   if good else (0, 0, 255)
    return status, issues, color, curr_Y, neck_angle, shoulder_diff

# ============================================================
#  UI 繪製
# ============================================================
def draw_ui(frame, state):
    """
    state = {
        "is_calibrated"  : bool,
        "status"         : str,
        "color"          : tuple,
        "issues"         : list,
        "bad_elapsed"    : float,
        "sitting_min"    : int,
        "good_pct"       : float,
        "curr_Y"         : float,
        "base_Y"         : float,
    }
    """
    h, w  = frame.shape[:2]
    pad   = 12
    box_w = 340
    box_h = 250

    # 背景框
    cv2.rectangle(frame, (pad, pad), (pad + box_w, pad + box_h), (40, 40, 40), -1)
    cv2.rectangle(frame, (pad, pad), (pad + box_w, pad + box_h), (110, 110, 110),  1)

    x, y = pad + 14, pad + 30

    if not state["is_calibrated"]:
        cv2.putText(frame, "Sit straight & press [C]", (x, y),
                    cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 255, 255), 1)
        return

    # 狀態
    cv2.putText(frame, state["status"], (x, y),
                cv2.FONT_HERSHEY_DUPLEX, 0.85, state["color"], 2)
    y += 32

    # 問題列表
    for issue in state["issues"]:
        cv2.putText(frame, f"  ! {issue}", (x, y),
                    cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 165, 255), 1)
        y += 24

    y = pad + 130
    # 高度數值
    cv2.putText(frame, f"Height  {state['curr_Y']:.4f}  (base {state['base_Y']:.4f})",
                (x, y), cv2.FONT_HERSHEY_DUPLEX, 0.5, (180, 180, 180), 1)
    y += 24

    # 不良姿勢持續進度條
    if state["bad_elapsed"] > 0:
        ratio    = min(state["bad_elapsed"] / BAD_POSTURE_WARN_SEC, 1.0)
        bar_full = box_w - 28
        bar_fill = int(ratio * bar_full)
        bar_y    = y + 6
        cv2.rectangle(frame, (x, bar_y), (x + bar_full, bar_y + 10), (80, 80, 80), -1)
        cv2.rectangle(frame, (x, bar_y), (x + bar_fill, bar_y + 10), (0, 165, 255), -1)
        cv2.putText(frame, f"Bad: {state['bad_elapsed']:.0f}s / {BAD_POSTURE_WARN_SEC}s",
                    (x, bar_y + 24), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 165, 255), 1)
    y += 42

    # 久坐 & 好姿勢比例
    sit_color = (0, 0, 255) if state["sitting_min"] >= SITTING_LIMIT_MIN else (200, 200, 200)
    cv2.putText(frame, f"Sitting: {state['sitting_min']} min", (x, pad + 220),
                cv2.FONT_HERSHEY_DUPLEX, 0.55, sit_color, 1)
    cv2.putText(frame, f"Good rate: {state['good_pct']:.0f}%", (x + 180, pad + 220),
                cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 220, 0), 1)

# ============================================================
#  主程式
# ============================================================
cap = cv2.VideoCapture(CAMERA_INDEX)

# 狀態變數
is_calibrated       = False
base                = {}          # 校準基準字典
session_start       = time.time()
last_save_time      = time.time()
last_stand_reminder = 0
bad_posture_start   = None
has_warned          = False
total_records       = 0
good_records        = 0

print(">>> System ready.  Sit straight and press [C] to calibrate.  [ESC] to quit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Camera read failed.")
        break

    frame  = cv2.flip(frame, 1)
    rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)
    key    = cv2.waitKey(1) & 0xFF

    # 預設值
    status, color, issues           = "WAITING", (200, 200, 200), []
    curr_Y, neck_angle, shoulder_diff = 0.0, 0.0, 0.0
    bad_elapsed                     = 0.0

    if result.pose_landmarks:
        lm = result.pose_landmarks.landmark

        # --- 校準 ---
        if key in (ord("c"), ord("C")):
            nose       = [lm[0].x, lm[0].y]
            l_ear      = [lm[7].x, lm[7].y]
            l_shoulder = [lm[11].x, lm[11].y]
            base = {
                "Y"            : (lm[11].y + lm[12].y) / 2 - (lm[9].y + lm[10].y) / 2,
                "neck_angle"   : calc_angle(nose, l_ear, l_shoulder),
                "shoulder_diff": abs(lm[11].y - lm[12].y),
            }
            is_calibrated     = True
            session_start     = time.time()
            bad_posture_start = None
            has_warned        = False
            print(f"Calibrated → Y={base['Y']:.4f}  neck={base['neck_angle']:.1f}°  shoulder={base['shoulder_diff']:.4f}")

        # --- 分析 ---
        if is_calibrated:
            status, issues, color, curr_Y, neck_angle, shoulder_diff = analyze_posture(lm, base)
            total_records += 1
            if status == "GOOD POSTURE":
                good_records     += 1
                bad_posture_start = None
                has_warned        = False
            else:
                if bad_posture_start is None:
                    bad_posture_start = time.time()
                bad_elapsed = time.time() - bad_posture_start
                if bad_elapsed >= BAD_POSTURE_WARN_SEC and not has_warned:
                    has_warned = True
                    show_popup_async(f"Bad posture for {BAD_POSTURE_WARN_SEC}s!\nPlease sit up straight.")

            # 久坐提醒
            sitting_sec = time.time() - session_start
            if sitting_sec >= SITTING_LIMIT_MIN * 60 and (time.time() - last_stand_reminder) > 60:
                last_stand_reminder = time.time()
                show_popup_async(f"You have been sitting for {SITTING_LIMIT_MIN} minutes.\nPlease stand up and stretch!")

            # CSV 存檔
            if (time.time() - last_save_time) >= SAVE_INTERVAL_SEC:
                t = time.strftime("%H:%M:%S")
                writer.writerow([t, f"{curr_Y:.4f}", f"{neck_angle:.1f}",
                                  f"{shoulder_diff:.4f}", status, "/".join(issues)])
                csv_file.flush()
                last_save_time = time.time()

        # 骨架
        mp_drawing.draw_landmarks(frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    # --- UI ---
    sitting_min = int((time.time() - session_start) // 60)
    good_pct    = (good_records / total_records * 100) if total_records > 0 else 0
    draw_ui(frame, {
        "is_calibrated": is_calibrated,
        "status"       : status,
        "color"        : color,
        "issues"       : issues,
        "bad_elapsed"  : bad_elapsed,
        "sitting_min"  : sitting_min,
        "good_pct"     : good_pct,
        "curr_Y"       : curr_Y,
        "base_Y"       : base.get("Y", 0.0),
    })

    cv2.imshow("AI Posture Guardian", frame)
    if key == 27:
        break

# ============================================================
#  結束
# ============================================================
cap.release()
csv_file.close()
cv2.destroyAllWindows()

if total_records > 0:
    good_pct = good_records / total_records * 100
    print(f"\n===== Session Report =====")
    print(f"Records   : {total_records}")
    print(f"Good      : {good_pct:.1f}%")
    print(f"Bad       : {100 - good_pct:.1f}%")
    print(f"Saved to  : posture_report_{today}.csv")
print(">>> Bye!")