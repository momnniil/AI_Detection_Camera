# ============================================================
#  config.py  ─ 所有可調參數集中在這裡
# ============================================================

CAMERA_INDEX = 0
SAVE_INTERVAL_SEC = 3
SITTING_LIMIT_MIN = 40
BAD_POSTURE_WARN_SEC = 30  # 持續不良姿勢幾秒後警告

# 姿勢門檻
THRESHOLD_HEAD_DROP = 0.04  # 低頭門檻（Y 掉落比例）
THRESHOLD_HUNCHING = 15  # 駝背門檻（角度差，與校準時比）
THRESHOLD_BODY_TILT = 0.02  # 歪斜門檻（肩膀高低差，與校準時比）

# 站立偵測：肩膀 Y 座標低於此比例視為站立（0.15 = 畫面頂端 15% 以內）
STAND_SHOULDER_Y_RATIO = 0.15

# 眼睛偵測
EYE_GAZE_STILL_SEC = 20  # 注視同一方向幾秒後警告
EYE_GAZE_MOVE_THRESH = 0.04  # 眼球移動門檻（歸一化座標差）
BLINK_RATE_WARN_MIN = 8  # 每分鐘眨眼次數低於此值才警告
BLINK_EAR_THRESH = 4.5  # Blink ratio 門檻（水平/垂直距離比，> 4.5 = 閉眼）
BLINK_CONSEC_FRAMES = 2  # 連續幾幀閉眼才算一次眨眼

# 異物/口罩偵測
MASK_COVER_RATIO = 0.30  # 嘴巴關鍵點被遮住比例門檻
OCCLUSION_SKIP_POSE = False  # 偵測到口罩時是否跳過姿勢警告（先關掉確認正常）
