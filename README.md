# AI Posture Guardian

即時偵測使用者坐姿、眼睛狀態與疲勞程度的 AI 健康監控系統。

---

## 功能

### 姿勢偵測
- 低頭 / 前傾（Forward/Head Drop）
- 駝背（Hunching）
- 身體歪斜（Body Tilt）
- 持續不良姿勢超過門檻時彈出警告視窗
- 久坐超過設定時間時提醒起身

### 眼睛偵測
- 眨眼頻率監控（EAR / Blink Ratio 演算法）
- 注視方向追蹤（MediaPipe Iris 虹膜關鍵點）
- 視距估算（虹膜幾何投影原理）
- 眨眼過少 / 注視同一位置太久時彈出警告

### 疲勞評分（Cross-Modal Fusion）
- 結合眨眼率、注視停留時間、不良姿勢持續時間
- 輸出疲勞分數（0–100）與等級：Fresh / Mild / Tired / Exhausted

### 報告匯出
- 每次工作階段結束自動產生 Excel 報表
- 包含姿勢分析圖（圓餅圖、不良類型分布、趨勢圖）
- 包含眼睛分析圖（眨眼率趨勢、注視趨勢、疲勞分數、疲勞等級）

---

## 環境需求

- Windows 10 / 11
- Python 3.11
- 網路攝影機（Webcam）

---

## 安裝步驟

### 1. 建立虛擬環境

```bash
python3.11 -m venv venv
venv\Scripts\activate
```

### 2. 安裝套件（方法一：一般安裝）

```bash
pip install "numpy==1.26.4" "protobuf==3.20.3" mediapipe opencv-python pandas matplotlib xlsxwriter
```

### 2. 安裝套件（方法二：若方法一失敗，改用預編譯版本）

```bash
.\venv\Scripts\python.exe -m pip install --only-binary=:all: "numpy==1.26.4" "protobuf==3.20.3" mediapipe opencv-python pandas matplotlib xlsxwriter
```

> ⚠️ 套件版本限制說明：
> - `numpy==1.26.4`：pandas 與 mediapipe 的共同相容版本
> - `protobuf==3.20.3`：mediapipe 0.10.9 要求 protobuf < 4，裝新版會衝突
> - `mediapipe`：需為 0.10.9 版，新版已移除 `solutions` API

### 3. 確認 mediapipe 版本

```bash
pip show mediapipe
```

若版本不是 0.10.9，手動指定：

```bash
pip install "mediapipe==0.10.9"
```

---
## 快速開始（已有 venv）

每次要使用時，只需要這兩行：
```bash
venv\Scripts\activate
.\venv\Scripts\python.exe main.py
```
結束程式按 ESC，會自動產生當天的 Excel 報表。

---
## 檔案結構

```
AI_Detection_Camera/
├── main.py               # 主程式（主迴圈）
├── config.py             # 所有可調參數
├── make_pic.py           # Excel 報表產生器
└── modules/
    ├── posture.py        # 姿勢分析
    ├── eye_tracker.py    # 眼睛偵測、視距、疲勞評分
    ├── face_guard.py     # 口罩 / 異物偵測
    ├── ui.py             # 畫面 UI 繪製
    ├── alert.py          # 彈跳警告視窗
    └── csv_logger.py     # CSV 資料記錄
```

---

## 執行方式

```bash
.\venv\Scripts\python.exe main.py
```

### 操作說明

| 按鍵 | 功能 |
|------|------|
| `C`  | 校準（坐直後按下，記錄當下姿勢為基準） |
| `ESC` | 結束程式，自動產生 Excel 報表 |

---

## 參數設定（config.py）

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `CAMERA_INDEX` | 0 | 攝影機編號 |
| `SAVE_INTERVAL_SEC` | 3 | CSV 記錄間隔（秒） |
| `SITTING_LIMIT_MIN` | 40 | 久坐提醒門檻（分鐘） |
| `BAD_POSTURE_WARN_SEC` | 30 | 不良姿勢警告門檻（秒） |
| `THRESHOLD_HEAD_DROP` | 0.04 | 低頭偵測門檻 |
| `THRESHOLD_HUNCHING` | 15 | 駝背偵測門檻（角度差） |
| `THRESHOLD_BODY_TILT` | 0.02 | 歪斜偵測門檻 |
| `EYE_GAZE_STILL_SEC` | 20 | 注視靜止警告門檻（秒） |
| `BLINK_RATE_WARN_MIN` | 8 | 眨眼率警告門檻（次/分鐘） |
| `BLINK_EAR_THRESH` | 4.5 | 閉眼判定門檻（blink ratio） |

---

## CSV 欄位說明

| 欄位 | 說明 |
|------|------|
| `Time` | 記錄時間 |
| `curr_Y` | 嘴巴到肩膀垂直距離（變小 = 低頭前傾） |
| `neck_angle` | 頸部角度（變小 = 駝背） |
| `shoulder_diff` | 左右肩高低差（變大 = 歪斜） |
| `Status` | GOOD POSTURE / BAD POSTURE |
| `Issues` | 具體問題（Forward/Head Drop、Hunching、Body Tilt） |
| `GazeStillSec` | 眼球靜止注視秒數 |
| `BlinkRateMin` | 每分鐘眨眼次數 |
| `DistanceCm` | 距離螢幕距離（cm） |
| `FatigueScore` | 疲勞分數（0–100） |
| `FatigueLabel` | 疲勞等級（Fresh / Mild / Tired / Exhausted） |

---

## 疲勞分數計算方式

```
疲勞分數 = 眨眼率分數（40%）+ 注視停留分數（35%）+ 姿勢分數（25%）

眨眼率分數  = max(0, (8 - 眨眼率) / 8) × 40
注視分數   = min(注視靜止秒數 / 20, 1.0) × 35
姿勢分數   = min(不良姿勢持續秒數 / 30, 1.0) × 25
```

| 分數區間 | 等級 |
|----------|------|
| 0 – 24 | Fresh |
| 25 – 49 | Mild |
| 50 – 74 | Tired |
| 75 – 100 | Exhausted |
