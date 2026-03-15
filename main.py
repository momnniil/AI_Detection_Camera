# import traceback
# import sys
# import ctypes
# import time
# import cv2
# import mediapipe as mp

# # ── 自己的模組 ──────────────────────────────────────────────
# import config
# from modules.alert import show_popup_async, reset_popup_flag
# from modules.posture import calibrate, analyze_posture, is_standing
# from modules.eye_tracker import EyeTracker
# from modules.face_guard import detect_mask, face_quality_ok
# from modules.ui import draw_ui
# from modules.csv_logger import CsvLogger

# # ── 取得螢幕解析度（Windows）──────────────────────────────
# user32 = ctypes.windll.user32
# screen_w = user32.GetSystemMetrics(0)
# screen_h = user32.GetSystemMetrics(1)

# try:
#     mp_pose = mp.solutions.pose
#     mp_face = mp.solutions.face_mesh
#     mp_drawing = mp.solutions.drawing_utils

#     pose = mp_pose.Pose(min_detection_confidence=0.7,
#                         min_tracking_confidence=0.7)
#     face_mesh = mp_face.FaceMesh(
#         max_num_faces=1,
#         refine_landmarks=True,
#         min_detection_confidence=0.6,
#         min_tracking_confidence=0.6,
#     )

#     logger = CsvLogger(interval_sec=config.SAVE_INTERVAL_SEC)
#     eye_tracker = EyeTracker()

#     is_calibrated = False
#     base = {}
#     session_start = time.time()
#     last_stand_remind = 0.0
#     bad_posture_start = None
#     has_warned_bad = False
#     total_records = 0
#     good_records = 0

#     cap = cv2.VideoCapture(config.CAMERA_INDEX)
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1920)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

#     cv2.namedWindow("AI Posture Guardian", cv2.WINDOW_NORMAL)
#     print(
#         ">>> System ready.  Sit straight and press [C] to calibrate.  [ESC] to quit.")

#     # ★ pending_calibrate：C 鍵在 imshow 後的 waitKey 抓到，
#     #   存起來下一幀開頭再消耗，避免被 MediaPipe 推論時間吃掉
#     pending_calibrate = False

#     while cap.isOpened():
#         ret, frame = cap.read()
#         if not ret:
#             print("Camera read failed.")
#             break

#         frame = cv2.flip(frame, 1)
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

#         # 消耗上一幀存下的旗標
#         do_calibrate = pending_calibrate
#         pending_calibrate = False

#         # ── MediaPipe 推論（慢，50-200ms）──────────────────
#         pose_result = pose.process(rgb)
#         face_result = face_mesh.process(rgb)

#         # ── 預設值 ──────────────────────────────────────────
#         status = "WAITING"
#         color = (200, 200, 200)
#         issues = []
#         curr_Y = 0.0
#         neck_angle = 0.0
#         shoulder_diff = 0.0
#         bad_elapsed = 0.0
#         standing = False
#         mask_detected = False
#         gaze_still_sec = 0.0
#         blink_rate_min = 0.0

#         # ── 臉部處理（FaceMesh）────────────────────────────
#         face_lm = None
#         if face_result.multi_face_landmarks:
#             face_lm = face_result.multi_face_landmarks[0].landmark

#             if face_quality_ok(face_lm):
#                 mask_detected = detect_mask(
#                     face_lm, frame)   # ← 傳入 frame 給模型裁臉

#                 img_h, img_w = frame.shape[:2]
#                 eye_warnings = eye_tracker.update(face_lm, img_w, img_h)
#                 info = eye_tracker.gaze_info
#                 gaze_still_sec = info["gaze_still_sec"]
#                 blink_rate_min = info["blink_rate_min"]

#                 for warn in eye_warnings:
#                     if warn == "GAZE_FIXATION":
#                         show_popup_async(
#                             f"You have been staring at the same spot\n"
#                             f"for {config.EYE_GAZE_STILL_SEC}s.\n"
#                             "Look away and rest your eyes!"
#                         )
#                     elif warn == "LOW_BLINK":
#                         show_popup_async(
#                             f"Blink rate too low ({blink_rate_min:.0f}/min).\n"
#                             "Remember to blink to prevent dry eyes!"
#                         )

#         # ── 骨架處理（Pose）────────────────────────────────
#         if pose_result.pose_landmarks:
#             lm = pose_result.pose_landmarks.landmark

#             standing = is_standing(lm)

#             if not standing:
#                 if do_calibrate:
#                     base = calibrate(lm)
#                     is_calibrated = True
#                     session_start = time.time()
#                     bad_posture_start = None
#                     has_warned_bad = False
#                     reset_popup_flag()
#                     eye_tracker.reset()
#                     print(
#                         f"Calibrated -> Y={base['Y']:.4f} "
#                         f"neck={base['neck_angle']:.1f}deg "
#                         f"shoulder={base['shoulder_diff']:.4f}"
#                     )

#                 if is_calibrated:
#                     skip_pose = mask_detected and config.OCCLUSION_SKIP_POSE

#                     if skip_pose:
#                         status = "MASK - SKIP POSE"
#                         color = (200, 200, 0)
#                     else:
#                         (status, issues, color,
#                          curr_Y, neck_angle, shoulder_diff) = analyze_posture(lm, base)

#                     total_records += 1

#                     if status == "GOOD POSTURE":
#                         good_records += 1
#                         bad_posture_start = None
#                         has_warned_bad = False
#                     elif not skip_pose:
#                         if bad_posture_start is None:
#                             bad_posture_start = time.time()
#                         bad_elapsed = time.time() - bad_posture_start
#                         if bad_elapsed >= config.BAD_POSTURE_WARN_SEC and not has_warned_bad:
#                             has_warned_bad = True
#                             show_popup_async(
#                                 f"Bad posture for {config.BAD_POSTURE_WARN_SEC}s!\n"
#                                 "Please sit up straight."
#                             )

#                     sitting_sec = time.time() - session_start
#                     if (sitting_sec >= config.SITTING_LIMIT_MIN * 60
#                             and (time.time() - last_stand_remind) > 60):
#                         last_stand_remind = time.time()
#                         show_popup_async(
#                             f"You have been sitting for {config.SITTING_LIMIT_MIN} minutes.\n"
#                             "Please stand up and stretch!"
#                         )

#                     logger.try_write(
#                         curr_Y, neck_angle, shoulder_diff, status, issues,
#                         gaze_still_sec, blink_rate_min
#                     )

#             mp_drawing.draw_landmarks(
#                 frame, pose_result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

#         # ── UI 繪製 ─────────────────────────────────────────
#         sitting_min = int((time.time() - session_start) // 60)
#         good_pct = (good_records / total_records *
#                     100) if total_records > 0 else 0.0

#         draw_ui(frame, {
#             "is_calibrated":  is_calibrated,
#             "status":         status,
#             "color":          color,
#             "issues":         issues,
#             "bad_elapsed":    bad_elapsed,
#             "sitting_min":    sitting_min,
#             "good_pct":       good_pct,
#             "curr_Y":         curr_Y,
#             "base_Y":         base.get("Y", 0.0),
#             "is_standing":    standing,
#             "mask_detected":  mask_detected,
#             "gaze_still_sec": gaze_still_sec,
#             "blink_rate_min": blink_rate_min,
#         })

#         # ── 顯示 ────────────────────────────────────────────
#         frame = cv2.resize(frame, (screen_w, screen_h))
#         cv2.imshow("AI Posture Guardian", frame)

#         # ★ waitKey 放在 imshow 之後才能正確收到按鍵
#         #   C 鍵存進 pending，下一幀消耗（MediaPipe 再慢都不會漏）
#         key = cv2.waitKey(1) & 0xFF
#         if key in (ord("c"), ord("C")):
#             pending_calibrate = True
#         if key == 27:   # ESC
#             break

#     cap.release()
#     logger.close()
#     cv2.destroyAllWindows()

#     if total_records > 0:
#         good_pct = good_records / total_records * 100
#         print("\n===== Session Report =====")
#         print(f"Records : {total_records}")
#         print(f"Good    : {good_pct:.1f}%")
#         print(f"Bad     : {100 - good_pct:.1f}%")

#     from make_pic import export_to_excel_with_chart
#     export_to_excel_with_chart()

import ctypes
import sys
import time
# except Exception as e:
#     traceback.print_exc()
#     input("Press Enter to close...")
# ============================================================
#  main.py  ─ AI Posture Guardian（主程式）
#  架構：main.py 只做「迴圈調度」，邏輯全在 modules/ 內
# ============================================================
import traceback

import cv2
import mediapipe as mp

# ── 自己的模組 ──────────────────────────────────────────────
import config
from modules.alert import reset_popup_flag, show_popup_async
from modules.csv_logger import CsvLogger
from modules.eye_tracker import EyeTracker
from modules.face_guard import detect_mask, face_quality_ok
from modules.posture import analyze_posture, calibrate, is_standing
from modules.ui import draw_ui

# ── 取得螢幕解析度（Windows）──────────────────────────────
user32 = ctypes.windll.user32
screen_w = user32.GetSystemMetrics(0)
screen_h = user32.GetSystemMetrics(1)

try:
    mp_pose = mp.solutions.pose
    mp_face = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils

    pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
    face_mesh = mp_face.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    )

    logger = CsvLogger(interval_sec=config.SAVE_INTERVAL_SEC)
    eye_tracker = EyeTracker()

    is_calibrated = False
    base = {}
    session_start = time.time()
    last_stand_remind = 0.0
    bad_posture_start = None
    has_warned_bad = False
    total_records = 0
    good_records = 0

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    cv2.namedWindow("AI Posture Guardian", cv2.WINDOW_NORMAL)
    print(">>> System ready.  Sit straight and press [C] to calibrate.  [ESC] to quit.")

    # ★ pending_calibrate：C 鍵在 imshow 後的 waitKey 抓到，
    #   存起來下一幀開頭再消耗，避免被 MediaPipe 推論時間吃掉
    pending_calibrate = False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed.")
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 消耗上一幀存下的旗標
        do_calibrate = pending_calibrate
        pending_calibrate = False

        # ── MediaPipe 推論（慢，50-200ms）──────────────────
        pose_result = pose.process(rgb)
        face_result = face_mesh.process(rgb)

        # ── 預設值 ──────────────────────────────────────────
        status = "WAITING"
        color = (200, 200, 200)
        issues = []
        curr_Y = 0.0
        neck_angle = 0.0
        shoulder_diff = 0.0
        bad_elapsed = 0.0
        standing = False
        mask_detected = False
        gaze_still_sec = 0.0
        blink_rate_min = 0.0
        distance_cm = -1.0
        fatigue_score = 0.0
        fatigue_label = "Fresh"

        # ── 臉部處理（FaceMesh）────────────────────────────
        face_lm = None
        if face_result.multi_face_landmarks:
            face_lm = face_result.multi_face_landmarks[0].landmark

            if face_quality_ok(face_lm):
                mask_detected = detect_mask(face_lm, frame)

                img_h, img_w = frame.shape[:2]
                eye_warnings = eye_tracker.update(
                    face_lm,
                    img_w,
                    img_h,
                    bad_posture_elapsed=bad_elapsed,  # 傳入姿勢持續時間給疲勞模型
                )
                info = eye_tracker.gaze_info
                gaze_still_sec = info["gaze_still_sec"]
                blink_rate_min = info["blink_rate_min"]
                distance_cm = info["distance_cm"]
                fatigue_score = info["fatigue_score"]
                fatigue_label = info["fatigue_label"]

                for warn in eye_warnings:
                    if warn == "GAZE_FIXATION":
                        show_popup_async(
                            f"You have been staring at the same spot\n"
                            f"for {config.EYE_GAZE_STILL_SEC}s.\n"
                            "Look away and rest your eyes!"
                        )
                    elif warn == "LOW_BLINK":
                        show_popup_async(
                            f"Blink rate too low ({blink_rate_min:.0f}/min).\n"
                            "Remember to blink to prevent dry eyes!"
                        )
                    elif warn == "TOO_CLOSE":
                        show_popup_async(
                            f"Too close to screen! ({distance_cm:.0f}cm)\n"
                            "Keep at least 50cm distance."
                        )

        # ── 骨架處理（Pose）────────────────────────────────
        if pose_result.pose_landmarks:
            lm = pose_result.pose_landmarks.landmark

            standing = is_standing(lm)

            if not standing:
                if do_calibrate:
                    base = calibrate(lm)
                    is_calibrated = True
                    session_start = time.time()
                    bad_posture_start = None
                    has_warned_bad = False
                    reset_popup_flag()
                    eye_tracker.reset()
                    print(
                        f"Calibrated -> Y={base['Y']:.4f} "
                        f"neck={base['neck_angle']:.1f}deg "
                        f"shoulder={base['shoulder_diff']:.4f}"
                    )

                if is_calibrated:
                    skip_pose = mask_detected and config.OCCLUSION_SKIP_POSE

                    if skip_pose:
                        status = "MASK - SKIP POSE"
                        color = (200, 200, 0)
                    else:
                        (status, issues, color, curr_Y, neck_angle, shoulder_diff) = (
                            analyze_posture(lm, base)
                        )

                    total_records += 1

                    if status == "GOOD POSTURE":
                        good_records += 1
                        bad_posture_start = None
                        has_warned_bad = False
                    elif not skip_pose:
                        if bad_posture_start is None:
                            bad_posture_start = time.time()
                        bad_elapsed = time.time() - bad_posture_start
                        if (
                            bad_elapsed >= config.BAD_POSTURE_WARN_SEC
                            and not has_warned_bad
                        ):
                            has_warned_bad = True
                            show_popup_async(
                                f"Bad posture for {config.BAD_POSTURE_WARN_SEC}s!\n"
                                "Please sit up straight."
                            )

                    sitting_sec = time.time() - session_start
                    if (
                        sitting_sec >= config.SITTING_LIMIT_MIN * 60
                        and (time.time() - last_stand_remind) > 60
                    ):
                        last_stand_remind = time.time()
                        show_popup_async(
                            f"You have been sitting for {config.SITTING_LIMIT_MIN} minutes.\n"
                            "Please stand up and stretch!"
                        )

                    logger.try_write(
                        curr_Y,
                        neck_angle,
                        shoulder_diff,
                        status,
                        issues,
                        gaze_still_sec,
                        blink_rate_min,
                        distance_cm,
                        fatigue_score,
                        fatigue_label,
                    )

            mp_drawing.draw_landmarks(
                frame, pose_result.pose_landmarks, mp_pose.POSE_CONNECTIONS
            )

        # ── UI 繪製 ─────────────────────────────────────────
        sitting_min = int((time.time() - session_start) // 60)
        good_pct = (good_records / total_records * 100) if total_records > 0 else 0.0

        draw_ui(
            frame,
            {
                "is_calibrated": is_calibrated,
                "status": status,
                "color": color,
                "issues": issues,
                "bad_elapsed": bad_elapsed,
                "sitting_min": sitting_min,
                "good_pct": good_pct,
                "curr_Y": curr_Y,
                "base_Y": base.get("Y", 0.0),
                "is_standing": standing,
                "mask_detected": mask_detected,
                "gaze_still_sec": gaze_still_sec,
                "blink_rate_min": blink_rate_min,
                "distance_cm": distance_cm,
                "fatigue_score": fatigue_score,
                "fatigue_label": fatigue_label,
            },
        )

        # ── 顯示 ────────────────────────────────────────────
        frame = cv2.resize(frame, (screen_w, screen_h))
        cv2.imshow("AI Posture Guardian", frame)

        # ★ waitKey 放在 imshow 之後才能正確收到按鍵
        #   C 鍵存進 pending，下一幀消耗（MediaPipe 再慢都不會漏）
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("c"), ord("C")):
            pending_calibrate = True
        if key == 27:  # ESC
            break

    cap.release()
    logger.close()
    cv2.destroyAllWindows()

    if total_records > 0:
        good_pct = good_records / total_records * 100
        print("\n===== Session Report =====")
        print(f"Records : {total_records}")
        print(f"Good    : {good_pct:.1f}%")
        print(f"Bad     : {100 - good_pct:.1f}%")

    from make_pic import export_to_excel_with_chart

    export_to_excel_with_chart()

except Exception as e:
    traceback.print_exc()
    input("Press Enter to close...")
