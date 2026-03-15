# # ============================================================
# #  modules/csv_logger.py  ─ CSV 存檔
# # ============================================================
# import csv
# import time
# from datetime import datetime


# class CsvLogger:
#     def __init__(self, interval_sec: int = 3):
#         self.interval = interval_sec
#         self._last_save = time.time()
#         today = datetime.now().strftime("%Y%m%d")
#         self._file = open(
#             f"posture_report_{today}.csv", "a", newline="", encoding="utf-8")
#         self._writer = csv.writer(self._file)
#         self._writer.writerow(["Time", "curr_Y", "neck_angle",
#                                "shoulder_diff", "Status", "Issues",
#                                "GazeStillSec", "BlinkRateMin"])

#     def try_write(self, curr_Y: float, neck_angle: float,
#                   shoulder_diff: float, status: str, issues: list[str],
#                   gaze_still_sec: float = 0.0,
#                   blink_rate_min: float = 0.0) -> bool:
#         """到達間隔才寫入，回傳 True 代表本次有寫入"""
#         if (time.time() - self._last_save) < self.interval:
#             return False
#         t = time.strftime("%H:%M:%S")
#         self._writer.writerow([
#             t,
#             f"{curr_Y:.4f}",
#             f"{neck_angle:.1f}",
#             f"{shoulder_diff:.4f}",
#             status,
#             "/".join(issues),
#             f"{gaze_still_sec:.1f}",
#             f"{blink_rate_min:.1f}",
#         ])
#         self._file.flush()
#         self._last_save = time.time()
#         return True

#     def close(self):
#         self._file.close()
# ============================================================
#  modules/csv_logger.py  ─ CSV 存檔
# ============================================================
import csv
import time
from datetime import datetime


class CsvLogger:
    def __init__(self, interval_sec: int = 3):
        self.interval = interval_sec
        self._last_save = time.time()
        today = datetime.now().strftime("%Y%m%d")
        self._file = open(
            f"posture_report_{today}.csv", "a", newline="", encoding="utf-8"
        )
        self._writer = csv.writer(self._file)
        self._writer.writerow(
            [
                "Time",
                "curr_Y",
                "neck_angle",
                "shoulder_diff",
                "Status",
                "Issues",
                "GazeStillSec",
                "BlinkRateMin",
                "DistanceCm",
                "FatigueScore",
                "FatigueLabel",
            ]
        )

    def try_write(
        self,
        curr_Y: float,
        neck_angle: float,
        shoulder_diff: float,
        status: str,
        issues: list[str],
        gaze_still_sec: float = 0.0,
        blink_rate_min: float = 0.0,
        distance_cm: float = -1.0,
        fatigue_score: float = 0.0,
        fatigue_label: str = "Fresh",
    ) -> bool:
        """到達間隔才寫入，回傳 True 代表本次有寫入"""
        if (time.time() - self._last_save) < self.interval:
            return False
        t = time.strftime("%H:%M:%S")
        self._writer.writerow(
            [
                t,
                f"{curr_Y:.4f}",
                f"{neck_angle:.1f}",
                f"{shoulder_diff:.4f}",
                status,
                "/".join(issues),
                f"{gaze_still_sec:.1f}",
                f"{blink_rate_min:.1f}",
                f"{distance_cm:.1f}",
                f"{fatigue_score:.1f}",
                fatigue_label,
            ]
        )
        self._file.flush()
        self._last_save = time.time()
        return True

    def close(self):
        self._file.close()
