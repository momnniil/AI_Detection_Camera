import cv2
import ctypes
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
csv_file = open(f"posture_report_{today}.csv", "a", newline="", encoding="utf-8")
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
#  數值 UI 繪製 (小黑窗)
# ============================================================
def draw_ui(frame, state):
    
    h, w  = frame.shape[:2]
    pad   = int(0.003 * w)
    box_w = int(0.3 * w)
    box_h = int(0.35 * h)
    
    # 字體大小距離左上角
    dis_x = int(0.01 * w)
    dis_y = int(0.06 * h)
    
    # 字體大小比例
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale_large = w / 1920 * 2   # 主狀態文字
    font_scale_med   = w / 1920 * 1  # 問題列表、久坐、好姿勢
    font_scale_small = w / 1920 * 0.9  # 進度條文字
    thickness_large  = max(2, int(w / 1920 * 2))
    thickness_med    = max(2, int(w / 1920 * 1))
    thickness_small  = max(1, int(w / 1920 * 1))
    
    # 計算行距，依字體高度自動
    _, line_height_large = cv2.getTextSize("A", font, font_scale_large, thickness_large)[:2]
    _, line_height_med   = cv2.getTextSize("A", font, font_scale_med, thickness_med)[:2]
    _, line_height_small = cv2.getTextSize("A", font, font_scale_small, thickness_small)[:2]

    # 背景框
    cv2.rectangle(frame, (pad, pad), (pad + box_w, pad + box_h), (40, 40, 40), -1)
    cv2.rectangle(frame, (pad, pad), (pad + box_w, pad + box_h), (110, 110, 110),  1)

    # 起始位置
    x, y = pad + dis_x, pad + dis_y

    if not state["is_calibrated"]:
        cv2.putText(frame, "Sit straight & press [C]", (x, y),
                    font, font_scale_med, (0, 255, 255), thickness_med)
        return

    # 主狀態文字
    cv2.putText(frame, state["status"], (x, y),
                font, font_scale_large, state["color"], thickness_large)
    y += line_height_large + int(h / 1080 * 4)   # 行距 + 4 px

    # 問題列表
    for issue in state["issues"]:
        cv2.putText(frame, f"  ! {issue}", (x, y+line_height_med),
                    font, font_scale_med, (0, 165, 255), thickness_med)
        y += line_height_med*3

    # 高度數值
    y = pad + int(0.12 * h)
    cv2.putText(frame, f"Height  {state['curr_Y']:.4f}  (base {state['base_Y']:.4f})",
                (x, int(box_h*0.5)), font, font_scale_small, (180, 180, 180), thickness_small)
    y += line_height_small + int(h / 1080 * 2)

    # 不良姿勢持續進度條
    if state["bad_elapsed"] > 0:
        ratio = min(state["bad_elapsed"] / BAD_POSTURE_WARN_SEC, 1.0)
        bar_full = box_w - int(h / 1080 * 28)
        bar_fill = int(ratio * bar_full)
        bar_y = y + int(0.075 * h)
        cv2.rectangle(frame, (x, bar_y), (x + bar_full, bar_y + 10), (80, 80, 80), -1)
        cv2.rectangle(frame, (x, bar_y), (x + bar_fill, bar_y + 10), (0, 165, 255), -1)
        cv2.putText(frame, f"Bad: {state['bad_elapsed']:.0f}s / {BAD_POSTURE_WARN_SEC}s",
                    (x, bar_y + int(0.04 * h)), font, font_scale_small, (0, 165, 255), thickness_small)
        
    y += line_height_small + int(h / 1080 * 18)

    # 久坐 & 好姿勢比例
    sit_color = (0, 0, 255) if state["sitting_min"] >= SITTING_LIMIT_MIN else (200, 200, 200)
    cv2.putText(frame, f"Sitting: {state['sitting_min']} min", (x, pad + int(0.3 * h)),
                font, font_scale_med, sit_color, thickness_med)
    cv2.putText(frame, f"Good rate: {state['good_pct']:.0f}%", 
                (x + int(0.15*w), pad + int(0.3 * h)),
                font, font_scale_med, (0, 220, 0), thickness_med)
                


# ============================================================
#  主程式
# ============================================================
cap = cv2.VideoCapture(CAMERA_INDEX)

# 設定相機畫質的樣子
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080) 

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
    
    # 可調整大小
    cv2.namedWindow("AI Posture Guardian", cv2.WINDOW_NORMAL) 
    # 將影像縮放到螢幕尺寸
    frame = cv2.resize(frame, (1920, 1080))
    
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