import cv2
import mediapipe as mp
import numpy as np
import csv
import time
from datetime import datetime
from collections import deque

# --- 初始化 MediaPipe ---
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# --- 初始化攝影機 ---
cap = cv2.VideoCapture(0)

# --- CSV 檔案設定 ---
today = datetime.now().strftime("%Y%m%d")
file = open(f"posture_report_{today}.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(file)
writer.writerow(["Time", "Mouth_to_Chest_Y", "Neck_Angle",
                "Shoulder_Diff", "Status", "Issues"])

# --- 核心變數 ---
is_calibrated = False
base_Y = 0.0
base_neck_angle = 0.0
base_shoulder_diff = 0.0
save_interval = 3.0
last_save_time = time.time()

# 久坐計時器
session_start = time.time()
SITTING_LIMIT = 40 * 60
last_stand_reminder = 0

# 統計數據
total_records = 0
good_records = 0

print(">>> System started!")
print(">>> Sit straight, switch to English input, press 'C' to calibrate.")


def calc_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))


def analyze_posture(lm, base_Y, base_neck_angle, base_shoulder_diff):
    issues = []

    # --- 指標 1：低頭 / 前傾 ---
    m_mid_y = (lm[9].y + lm[10].y) / 2
    s_mid_y = (lm[11].y + lm[12].y) / 2
    curr_Y = s_mid_y - m_mid_y
    y_drop = base_Y - curr_Y
    if y_drop > 0.04:
        issues.append("Forward/Head Drop")

    # --- 指標 2：駝背（與校準角度比較）---
    nose = [lm[0].x, lm[0].y]
    l_ear = [lm[7].x, lm[7].y]
    l_shoulder = [lm[11].x, lm[11].y]
    neck_angle = calc_angle(nose, l_ear, l_shoulder)
    if (base_neck_angle - neck_angle) > 15:
        issues.append("Hunching")

    # --- 指標 3：身體歪斜（與校準差值比較）---
    shoulder_diff = abs(lm[11].y - lm[12].y)
    if (shoulder_diff - base_shoulder_diff) > 0.02:
        issues.append("Body Tilt")

    if not issues:
        return "GOOD POSTURE", [], (0, 200, 0), curr_Y, neck_angle, shoulder_diff
    else:
        return "BAD POSTURE", issues, (0, 0, 255), curr_Y, neck_angle, shoulder_diff


while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

    key = cv2.waitKey(1) & 0xFF  # 移到外層避免 Bug
    status = "WAITING FOR CALIBRATION"
    color = (200, 200, 200)
    curr_Y = 0.0
    issues = []
    neck_angle = 0.0
    shoulder_diff = 0.0

    if result.pose_landmarks:
        lm = result.pose_landmarks.landmark

        m_mid_x = (lm[9].x + lm[10].x) / 2
        m_mid_y = (lm[9].y + lm[10].y) / 2
        s_mid_x = (lm[11].x + lm[12].x) / 2
        s_mid_y = (lm[11].y + lm[12].y) / 2
        curr_Y = s_mid_y - m_mid_y

        # 校準：按 C 同時記錄三個基準值
        if key == ord("c") or key == ord("C"):
            base_Y = curr_Y
            nose = [lm[0].x, lm[0].y]
            l_ear = [lm[7].x, lm[7].y]
            l_shoulder = [lm[11].x, lm[11].y]
            base_neck_angle = calc_angle(nose, l_ear, l_shoulder)
            base_shoulder_diff = abs(lm[11].y - lm[12].y)
            is_calibrated = True
            session_start = time.time()
            print(
                f"Calibrated! base_Y={base_Y:.4f}, neck={base_neck_angle:.1f}, shoulder={base_shoulder_diff:.4f}")

        if is_calibrated:
            status, issues, color, curr_Y, neck_angle, shoulder_diff = analyze_posture(
                lm, base_Y, base_neck_angle, base_shoulder_diff
            )

            # 統計
            total_records += 1
            if status == "GOOD POSTURE":
                good_records += 1

            # 久坐提醒
            sitting_time = time.time() - session_start
            if sitting_time >= SITTING_LIMIT and (time.time() - last_stand_reminder) > 60:
                last_stand_reminder = time.time()
                print("You have been sitting for 40 minutes. Please stand up!")

            # 定時存檔
            if (time.time() - last_save_time) >= save_interval:
                readable_time = time.strftime("%H:%M:%S")
                writer.writerow([readable_time, f"{curr_Y:.4f}", f"{neck_angle:.1f}",
                                 f"{shoulder_diff:.4f}", status, "/".join(issues)])
                file.flush()
                last_save_time = time.time()
                print(f"Log saved: {readable_time} - {status}")

        # --- 視覺化儀表板（保留原版風格）---
        cv2.rectangle(frame, (10, 10), (380, 240), (60, 60, 60), -1)
        cv2.rectangle(frame, (10, 10), (380, 240), (100, 100, 100), 1)

        cv2.putText(frame, f"LIVE Height: {curr_Y:.4f}", (25, 40),
                    cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 0), 1)

        if is_calibrated:
            cv2.putText(frame, f"BASE Height: {base_Y:.4f}", (25, 68),
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, (180, 180, 180), 1)
            cv2.putText(frame, status, (25, 105),
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, color, 2)

            # 顯示問題項目
            for i, issue in enumerate(issues):
                cv2.putText(frame, f"  ! {issue}", (25, 132 + i * 24),
                            cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 165, 255), 1)

            # 久坐計時
            sitting_min = int((time.time() - session_start) // 60)
            sit_color = (0, 0, 255) if sitting_min >= 40 else (200, 200, 200)
            cv2.putText(frame, f"Sitting: {sitting_min} min", (25, 210),
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, sit_color, 1)

            # 好姿勢比例
            if total_records > 0:
                good_pct = good_records / total_records * 100
                cv2.putText(frame, f"Good: {good_pct:.0f}%", (220, 210),
                            cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)
        else:
            cv2.putText(frame, "PLEASE PRESS 'C'", (25, 90),
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 255), 2)

        # 頭部到肩膀連線
        cv2.line(frame,
                 (int(m_mid_x * w), int(m_mid_y * h)),
                 (int(s_mid_x * w), int(s_mid_y * h)),
                 (0, 255, 255), 2)

        mp_drawing.draw_landmarks(
            frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    cv2.imshow("AI Posture Guardian", frame)
    if key == 27:
        break

# --- 清理資源 ---
cap.release()
file.close()
cv2.destroyAllWindows()

if total_records > 0:
    good_pct = good_records / total_records * 100
    print(f"\n===== Today's Report =====")
    print(f"Total records : {total_records}")
    print(f"Good posture  : {good_pct:.1f}%")
    print(f"Bad posture   : {100 - good_pct:.1f}%")
    print(f"Saved to posture_report_{today}.csv")
print(">>> Program closed.")
