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
file = open("posture_log_3s.csv", "w", newline="")
writer = csv.writer(file)
writer.writerow(["timestamp", "time_readable", "nose_y", "offset_x", "status"])

# --- 變數初始化 ---
baseline_offset = 0.05
is_calibrated = False
save_interval = 3.0      # 設定 3 秒記錄一次
last_save_time = time.time()

print("程式啟動！請坐正後按下 'C' 鍵進行姿勢校準。")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1) # 鏡像畫面
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

    status = "Waiting for Calibration"
    color = (255, 255, 255)
    current_offset = 0

    if result.pose_landmarks:
        lm = result.pose_landmarks.landmark
        
        # 取得關鍵點
        nose = [lm[0].x, lm[0].y]
        l_sh = [lm[11].x, lm[11].y]
        r_sh = [lm[12].x, lm[12].y]

        # 計算肩中點
        sh_mid_x = (l_sh[0] + r_sh[0]) / 2
        sh_mid_y = (l_sh[1] + r_sh[1]) / 2

        # 烏龜頸偏移量 (水平距離)
        current_offset = abs(nose[0] - sh_mid_x)

        # 1. 校準邏輯
        key = cv2.waitKey(1)
        if key & 0xFF == ord('c'):
            baseline_offset = current_offset
            is_calibrated = True
            print(f"校準完成！當前基準: {baseline_offset:.4f}")
        

        # --- 改進後的姿勢判斷 ---
        if is_calibrated:
            # A. 烏龜頸判斷：水平位移 (X 軸) 增加
            # 將 0.07 調降至 0.04 (可根據你的距離微調)
            is_turtle = (current_offset - baseline_offset) > 0.04 

            # B. 低頭/前傾判斷：鼻子與肩中點的垂直距離 (Y 軸)
            # 當頭往前伸或低頭，這個垂直距離會明顯變小
            current_y_dist = sh_mid_y - nose[1]
            is_drooping = current_y_dist < 0.10  # 數字愈大愈嚴格

            if is_turtle:
                status = "Bad (Forward Head)"
                color = (0, 0, 255) # 紅色
            elif is_drooping:
                status = "Bad (Drooping)"
                color = (0, 165, 255) # 橘色
            else:
                status = "Good"
                color = (0, 255, 0) # 綠色

        # # 2. 姿勢判斷
        # if is_calibrated:
        #     # 判斷烏龜頸或低頭
        #     if (current_offset - baseline_offset) > 0.07:
        #         status = "Bad (Forward Head)"
        #         color = (0, 0, 255)
        #     elif (sh_mid_y - nose[1]) < 0.15: # 鼻子與肩膀垂直距離太短
        #         status = "Bad (Drooping)"
        #         color = (0, 165, 255)
        #     else:
        #         status = "Good"
        #         color = (0, 255, 0)

            # 3. 每三秒記錄一次數據
            current_time = time.time()
            if (current_time - last_save_time) >= save_interval:
                readable_time = time.strftime("%H:%M:%S", time.localtime(current_time))
                writer.writerow([current_time, readable_time, nose[1], current_offset, status])
                file.flush() # 確保數據即時寫入硬碟
                last_save_time = current_time
                print(f"數據已記錄: {readable_time} - {status}")

        # --- 視覺顯示 ---
        h, w, _ = frame.shape
        # 畫出偵測線
        cv2.line(frame, (int(nose[0]*w), int(nose[1]*h)), (int(sh_mid_x*w), int(sh_mid_y*h)), (255, 0, 0), 2)
        
        cv2.putText(frame, f"Status: {status}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        if not is_calibrated:
            cv2.putText(frame, "Press 'C' to Calibrate", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        else:
            # 倒數計時下次紀錄 (可選)
            next_record = int(save_interval - (time.time() - last_save_time))
            cv2.putText(frame, f"Next Log in: {next_record}s", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        mp_drawing.draw_landmarks(frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    cv2.imshow("AI Office Guardian", frame)
    if cv2.waitKey(1) & 0xFF == 27: break # ESC 退出

cap.release()
file.close()
cv2.destroyAllWindows()