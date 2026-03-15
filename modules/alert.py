# ============================================================
#  modules/alert.py  ─ 彈跳警告視窗（永遠最前、只跳一次）
# ============================================================
import ctypes
import threading

# 追蹤目前是否有 popup 正在顯示，避免重複彈出
_popup_showing = False
_popup_lock = threading.Lock()


def show_popup_async(message: str) -> None:
    """
    在背景執行緒彈出提示。
    - 視窗永遠在最前（TOPMOST）
    - 同一時間只會有一個 popup，不重複堆疊
    """
    global _popup_showing

    with _popup_lock:
        if _popup_showing:
            return  # 已有 popup，直接略過
        _popup_showing = True

    def _popup():
        global _popup_showing
        try:
            # MB_ICONWARNING | MB_SYSTEMMODAL
            # MB_SYSTEMMODAL (0x1000) 讓視窗強制置頂並搶焦點
            MB_ICONWARNING = 0x30
            MB_SYSTEMMODAL = 0x1000
            flags = MB_ICONWARNING | MB_SYSTEMMODAL
            ctypes.windll.user32.MessageBoxW(0, message, "AI Posture Warning", flags)
        finally:
            with _popup_lock:
                _popup_showing = False  # 使用者關閉後重置，才能再次警告

    threading.Thread(target=_popup, daemon=True).start()


def reset_popup_flag() -> None:
    """外部強制重置（例如重新校準時呼叫）"""
    global _popup_showing
    with _popup_lock:
        _popup_showing = False
