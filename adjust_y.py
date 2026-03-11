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
cap = cv2.VideoCapture(1)

# --- CSV 檔案設定 ---
file = open("posture_analysis_report.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(file)
writer.writerow(["Time", "Mouth_to_Chest_Y", "Status"])

# --- 核心變數 ---
is_calibrated = False
base_Y = 0.0          # 基準垂直高度
save_interval = 3.0    # 每 3 秒紀錄一次
last_save_time = time.time()

print(">>> 系統啟動成功！")
print(">>> 請先『坐正』，確保輸入法為『英文』，對著視窗按下鍵盤上的 'C' 進行校準。")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 1. 影像預處理
    frame = cv2.flip(frame, 1)  # 鏡像處理
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

    status = "WAITING FOR CALIBRATION"
    color = (200, 200, 200) # 灰色：等待中
    curr_Y = 0.0

    if result.pose_landmarks:
        lm = result.pose_landmarks.landmark

        # 2. 取得關鍵點 (使用標準化座標)
        # 嘴巴中心點 (取左右嘴角的中點)
        m_mid_x = (lm[9].x + lm[10].x) / 2
        m_mid_y = (lm[9].y + lm[10].y) / 2
        
        # 胸口基準點 (取左右肩的中點)
        s_mid_x = (lm[11].x + lm[12].x) / 2
        s_mid_y = (lm[11].y + lm[12].y) / 2

        # 3. 計算垂直高度差 (正面鏡頭最重要的指標)
        # 坐正時，嘴巴與肩膀的高度差最大；前傾或低頭時，高度差會變小。
        curr_Y = s_mid_y - m_mid_y

        # 4. 捕捉按鍵事件 (增加等待時間確保捕捉)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('c') or key == ord('C'):
            base_Y = curr_Y
            is_calibrated = True
            print(f"✅ 校準完成！您的基準高度為: {base_Y:.4f}")

        # 5. 姿勢判斷邏輯
        if is_calibrated:
            # 計算高度掉落量 (原本的高度 - 現在的高度)
            y_drop = base_Y - curr_Y

            # 門檻值建議：0.04 (約畫面高度的 4%)，若太靈敏可調大，不靈敏可調小
            if y_drop > 0.04:
                status = "BAD: FORWARD / DROOPING"
                color = (0, 0, 255)  # 紅色：警告
            else:
                status = "GOOD POSTURE"
                color = (0, 255, 0)  # 綠色：良好

            # 6. 定時記錄數據 (每 3 秒一次)
            if (time.time() - last_save_time) >= save_interval:
                readable_time = time.strftime("%H:%M:%S")
                writer.writerow([readable_time, f"{curr_Y:.4f}", status])
                file.flush()
                last_save_time = time.time()
                print(f"Log saved: {readable_time} - {status}")

        # --- 7. 視覺化儀表板 ---
        # 繪製半透明資訊框
        cv2.rectangle(frame, (10, 10), (320, 140), (60, 60, 60), -1)
        
        # 標示即時 Y 軸數值 (垂直距離)
        cv2.putText(frame, f"LIVE Height: {curr_Y:.4f}", (25, 40), 
                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 0), 1)
        
        if is_calibrated:
            cv2.putText(frame, f"BASE Height: {base_Y:.4f}", (25, 70), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, (180, 180, 180), 1)
            cv2.putText(frame, status, (25, 110), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, color, 2)
        else:
            cv2.putText(frame, "PLEASE PRESS 'C'", (25, 90), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 255), 2)

        # 在畫面上畫出一條「連線」，直觀顯示頭部與軀幹的壓縮感
        cv2.line(frame, (int(m_mid_x*w), int(m_mid_y*h)), 
                 (int(s_mid_x*w), int(s_mid_y*h)), (0, 255, 255), 2)
        
        # 畫出骨架輔助點
        mp_drawing.draw_landmarks(frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    # 顯示視窗
    cv2.imshow("AI Posture Guard V4 (Frontal View)", frame)

    # 按 ESC 鍵退出
    if key == 27:
        break

# --- 清理資源 ---
cap.release()
file.close()
cv2.destroyAllWindows()
print(">>> 程式已關閉，數據已儲存至 posture_analysis_report.csv")