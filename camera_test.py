import cv2
import ctypes

# 取得螢幕解析度
user32 = ctypes.windll.user32
screen_w = user32.GetSystemMetrics(0)
screen_h = user32.GetSystemMetrics(1)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)  # 可調整大小

while True:
    ret, frame = cap.read()
    if not ret:
        print("frame error")
        break

    # 將影像縮放到螢幕尺寸
    frame_resized = cv2.resize(frame, (screen_w, screen_h))

    cv2.imshow("Camera", frame_resized)

    if cv2.waitKey(1) == 27:  # ESC 鍵退出
        break

cap.release()
cv2.destroyAllWindows()