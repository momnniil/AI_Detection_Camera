import cv2
import mediapipe as mp
import numpy as np
import csv
import time

# 初始化 mediapipe
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# 開啟攝影機 (0=內建鏡頭)
cap = cv2.VideoCapture(0)

# CSV設定
file = open("posture_log.csv", "w", newline="")
writer = csv.writer(file)
writer.writerow(["time", "distance", "status"])

# 變數
is_calibrated = False
baseline_dist = 0
last_save_time = time.time()
save_interval = 3

print("程式啟動！坐正後按 C 校準")

while cap.isOpened():

    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    result = pose.process(rgb)

    status = "Waiting Calibration"
    color = (255,255,255)
    dist = 0

    if result.pose_landmarks:

        lm = result.pose_landmarks.landmark

        # 嘴巴
        mouth_l = np.array([lm[9].x, lm[9].y])
        mouth_r = np.array([lm[10].x, lm[10].y])

        # 肩膀
        sh_l = np.array([lm[11].x, lm[11].y])
        sh_r = np.array([lm[12].x, lm[12].y])

        # 中點
        mouth_mid = (mouth_l + mouth_r)/2
        chest_mid = (sh_l + sh_r)/2

        # 距離
        dist = np.linalg.norm(mouth_mid - chest_mid)

        # 按鍵
        key = cv2.waitKey(1) & 0xFF

        if key == ord('c'):
            baseline_dist = dist
            is_calibrated = True
            print("校準完成:", baseline_dist)

        if is_calibrated:

            # 偵測駝背
            if dist < baseline_dist * 0.85:

                status = "BAD POSTURE"
                color = (0,0,255)

            else:

                status = "GOOD POSTURE"
                color = (0,255,0)

        # 每3秒存資料
        if time.time() - last_save_time > save_interval:

            writer.writerow([
                time.strftime("%H:%M:%S"),
                round(dist,4),
                status
            ])

            file.flush()
            last_save_time = time.time()

        # 畫線
        cv2.line(
            frame,
            (int(mouth_mid[0]*w), int(mouth_mid[1]*h)),
            (int(chest_mid[0]*w), int(chest_mid[1]*h)),
            (255,0,0),
            2
        )

        mp_drawing.draw_landmarks(
            frame,
            result.pose_landmarks,
            mp_pose.POSE_CONNECTIONS
        )

    # UI
    cv2.rectangle(frame,(10,10),(320,120),(0,0,0),-1)

    cv2.putText(frame,
        f"Dist: {dist:.4f}",
        (20,40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0,255,255),
        2)

    cv2.putText(frame,
        f"Base: {baseline_dist:.4f}",
        (20,70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (200,200,200),
        1)

    cv2.putText(frame,
        status,
        (20,100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2)

    cv2.imshow("Posture Monitor", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
file.close()
cv2.destroyAllWindows()