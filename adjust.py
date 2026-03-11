import cv2
import mediapipe as mp
import numpy as np
import csv
import time

# 初始化 mediapipe
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(1)

# CSV 設定
file = open("posture_log_final.csv", "w", newline="")
writer = csv.writer(file)
writer.writerow(["time", "mouth_chest_dist", "status"])

# --- 變數初始化 ---
is_calibrated = False
baseline_dist = 0.0
save_interval = 3.0
last_save_time = time.time()

print("程式啟動！請坐正後按下 'C' 鍵校準。")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1) # 鏡像
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

    status = "Waiting for Calibration"
    color = (255, 255, 255)
    dist_display = 0.0

    if result.pose_landmarks:
        lm = result.pose_landmarks.landmark
        
        # 1. 取得關鍵點 (嘴巴兩角與兩肩)
        l_mouth = np.array([lm[9].x, lm[9].y])
        r_mouth = np.array([lm[10].x, lm[10].y])
        l_sh = np.array([lm[11].x, lm[11].y])
        r_sh = np.array([lm[12].x, lm[12].y])

        # 2. 計算中點
        mouth_mid = (l_mouth + r_mouth) / 2
        chest_mid = (l_sh + r_sh) / 2

        # 3. 計算「水平距離」(X軸差值) 作為烏龜頸指標
        # 如果你坐側一點，這個數值變化會非常明顯
        dist_display = abs(mouth_mid[0] - chest_mid[0])

        # 4. 校準與判斷
        key = cv2.waitKey(1)
        if key & 0xFF == ord('c'):
            baseline_dist = dist_display
            is_calibrated = True
            print(f"校準完成！基準距離: {baseline_dist:.4f}")

        # --- 專為正面鏡頭設計的邏輯 ---

            if is_calibrated:
                # 1. 計算 Y 軸縮短量 (高度塌陷)
                # 坐正時 base_Y 較大(如 0.25)，前傾低頭時 curr_Y 較小(如 0.18)
                y_drop = base_Y - curr_Y

                # 2. 判斷邏輯
                # 在正面視角下，Y 軸縮短 0.03 ~ 0.05 通常就代表姿勢走樣了
                if y_drop > 0.04:
                    status = "BAD: Drooping / Forward"
                    color = (0, 0, 255) # 紅色
                else:
                    status = "GOOD"
                    color = (0, 255, 0) # 綠色

            # 5. 每三秒記錄
            if (time.time() - last_save_time) >= save_interval:
                writer.writerow([time.strftime("%H:%M:%S"), f"{dist_display:.4f}", status])
                file.flush()
                last_save_time = time.time()

        # --- 視覺標記 ---
        # 在左上角標示即時數值
        cv2.rectangle(frame, (10, 10), (250, 120), (0, 0, 0), -1) # 黑底背景增加閱讀性
        cv2.putText(frame, f"Dist: {dist_display:.4f}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"Base: {baseline_dist:.4f}", (20, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(frame, status, (20, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 畫出嘴巴到胸線的連線，方便肉眼確認
        cv2.line(frame, (int(mouth_mid[0]*w), int(mouth_mid[1]*h)), 
                 (int(chest_mid[0]*w), int(chest_mid[1]*h)), (255, 0, 0), 2)

        mp_drawing.draw_landmarks(frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    cv2.imshow("Posture Monitor", frame)
    if cv2.waitKey(1) & 0xFF == 27: break

cap.release()
file.close()
cv2.destroyAllWindows()