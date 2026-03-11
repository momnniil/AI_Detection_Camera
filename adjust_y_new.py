import cv2
import mediapipe as mp
import numpy as np
import csv
import time

# --- 初始化 MediaPipe ---
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# --- 初始化攝影機 ---
cap = cv2.VideoCapture(0)

# --- CSV 檔案設定 ---
file = open("posture_analysis_report.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(file)
writer.writerow(["Time", "Mouth_to_Chest_Y", "Status"])

# --- 核心變數 ---
is_calibrated = False
base_Y = 0.0          
save_interval = 3.0    
last_save_time = time.time()

print(">>> 系統啟動成功！")
print(">>> 請先『坐正』，確保輸入法為『英文』，對著視窗按下鍵盤上的 'C' 進行校準。")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 1. 影像預處理
    frame = cv2.flip(frame, 1)  
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

    # 【重要修正】：將 key 移出 if 區塊，確保每一幀都有定義
    key = cv2.waitKey(1) & 0xFF

    status = "WAITING FOR CALIBRATION"
    color = (200, 200, 200) 
    curr_Y = 0.0

    if result.pose_landmarks:
        lm = result.pose_landmarks.landmark

        # 2. 取得關鍵點
        m_mid_y = (lm[9].y + lm[10].y) / 2 # 嘴巴中點 Y
        s_mid_x = (lm[11].x + lm[12].x) / 2 # 胸口中點 X (畫線用)
        s_mid_y = (lm[11].y + lm[12].y) / 2 # 胸口中點 Y

        # 3. 計算垂直高度差
        curr_Y = s_mid_y - m_mid_y

        # 4. 捕捉按鍵事件 (C 鍵校準)
        if key == ord('c') or key == ord('C'):
            base_Y = curr_Y
            is_calibrated = True
            print(f"✅ 校準成功！基準高度: {base_Y:.4f}")

        # 5. 姿勢判斷邏輯
        if is_calibrated:
            y_drop = base_Y - curr_Y
            if y_drop > 0.04:
                status = "BAD: FORWARD / DROOPING"
                color = (0, 0, 255) 
            else:
                status = "GOOD POSTURE"
                color = (0, 255, 0) 

            # 6. 定時記錄 (3秒一次)
            if (time.time() - last_save_time) >= save_interval:
                readable_time = time.strftime("%H:%M:%S")
                writer.writerow([readable_time, f"{curr_Y:.4f}", status])
                file.flush()
                last_save_time = time.time()

        # --- 7. 視覺化繪製 ---
        cv2.rectangle(frame, (10, 10), (320, 140), (40, 40, 40), -1)
        cv2.putText(frame, f"LIVE Height: {curr_Y:.4f}", (25, 40), 1, 1.2, (255, 255, 0), 2)
        
        if is_calibrated:
            cv2.putText(frame, f"BASE Height: {base_Y:.4f}", (25, 70), 1, 1.0, (180, 180, 180), 1)
            cv2.putText(frame, status, (25, 110), 1, 1.2, color, 2)
        else:
            cv2.putText(frame, "PLEASE PRESS 'C'", (25, 90), 1, 1.2, (0, 255, 255), 2)

        # 繪製標記與骨架
        m_x = int(((lm[9].x + lm[10].x) / 2) * w)
        m_y = int(m_mid_y * h)
        s_x = int(s_mid_x * w)
        s_y = int(s_mid_y * h)
        cv2.line(frame, (m_x, m_y), (s_x, s_y), (0, 255, 255), 2)
        mp_drawing.draw_landmarks(frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    # 顯示視窗
    cv2.imshow("AI Posture Guard V4", frame)

    # 8. 退出判斷 (ESC 鍵)
    if key == 27:
        break

cap.release()
file.close()
cv2.destroyAllWindows()