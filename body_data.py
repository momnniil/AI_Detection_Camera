import cv2
import mediapipe as mp
import time
import csv


mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

cap = cv2.VideoCapture(1)

while True:
    ret, frame = cap.read()

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

    # 如果偵測到人體
    if result.pose_landmarks:

        # 取得所有關鍵點
        landmarks = result.pose_landmarks.landmark

        # 取得特定點
        nose = landmarks[0]
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_hip = landmarks[23]

        print("Nose:", nose.x, nose.y)
        print("Left Shoulder:", left_shoulder.x, left_shoulder.y)

        # 畫骨架
        mp.solutions.drawing_utils.draw_landmarks(
            frame,
            result.pose_landmarks,
            mp_pose.POSE_CONNECTIONS
        )

    cv2.imshow("Pose Detection", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()