import cv2
import mediapipe as mp
import numpy as np
import csv
import time

# 初始化 mediapipe pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

# 初始化 webcam
cap = cv2.VideoCapture(0)

# 建立 CSV 檔案
file = open("pose_data.csv", "w", newline="")
writer = csv.writer(file)

writer.writerow([
    "time",
    "nose_x","nose_y",
    "left_shoulder_x","left_shoulder_y",
    "right_shoulder_x","right_shoulder_y",
    "left_hip_x","left_hip_y",
    "angle",
    "posture"
])

# 計算角度函式
def calculate_angle(a, b, c):

    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    ba = a - b
    bc = c - b

    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.degrees(np.arccos(cosine))

    return angle


while True:

    ret, frame = cap.read()

    if not ret:
        break

    # BGR → RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # AI 偵測姿勢
    result = pose.process(rgb)

    posture = "Unknown"
    angle = 0

    if result.pose_landmarks:

        landmarks = result.pose_landmarks.landmark

        nose = landmarks[0]
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_hip = landmarks[23]

        # 轉成座標
        head = [nose.x, nose.y]
        shoulder = [left_shoulder.x, left_shoulder.y]
        hip = [left_hip.x, left_hip.y]

        # 計算角度
        angle = calculate_angle(head, shoulder, hip)

        # 姿勢判斷
        if angle < 150:
            posture = "Bad"
        else:
            posture = "Good"

        # 寫入 CSV
        writer.writerow([
            time.time(),
            nose.x, nose.y,
            left_shoulder.x, left_shoulder.y,
            right_shoulder.x, right_shoulder.y,
            left_hip.x, left_hip.y,
            angle,
            posture
        ])

        # 顯示角度
        cv2.putText(
            frame,
            f"Angle: {int(angle)}",
            (30,50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255,255,255),
            2
        )

        # 姿勢提醒
        if posture == "Bad":

            cv2.putText(
                frame,
                "Bad Posture!",
                (30,100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0,0,255),
                2
            )

        else:

            cv2.putText(
                frame,
                "Good Posture",
                (30,100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0,255,0),
                2
            )

        # 畫骨架
        mp.solutions.drawing_utils.draw_landmarks(
            frame,
            result.pose_landmarks,
            mp_pose.POSE_CONNECTIONS
        )

    # 顯示畫面
    cv2.imshow("AI Posture Guardian", frame)

    # ESC 離開
    if cv2.waitKey(1) & 0xFF == 27:
        break

# 關閉
cap.release()
file.close()
cv2.destroyAllWindows()