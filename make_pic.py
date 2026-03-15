import os
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd

today = datetime.now().strftime("%Y%m%d")
csv_file = f"posture_report_{today}.csv"
excel_file = f"Posture_Analysis_Report_{today}.xlsx"
temp_posture = "temp_posture_chart.png"
temp_eye = "temp_eye_chart.png"


# ── 工具：取校準基準值 ────────────────────────────────────────
def _base_values(df):
    base_data = df[df["Issues"] == "CALIBRATED_BASE"]
    if not base_data.empty:
        row = base_data.iloc[-1]
        return float(row["neck_angle"]), float(row["curr_Y"]), row["Time"][:5]
    return (
        float(df["neck_angle"].iloc[0]),
        float(df["curr_Y"].iloc[0]),
        df["Minute"].iloc[0],
    )


# ── 圖一：姿勢相關（2x2）────────────────────────────────────
def _make_posture_chart(df, df_min):
    base_angle, base_y_val, base_time = _base_values(df)
    step = max(1, len(df_min) // 8)

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(f"Posture Analysis Report - {today}", fontsize=14, fontweight="bold")

    # [0,0] 圓餅圖
    sc = df["Status"].value_counts()
    axes[0, 0].pie(
        [sc.get("GOOD POSTURE", 0), sc.get("BAD POSTURE", 0)],
        labels=["Good", "Bad"],
        colors=["#2ecc71", "#e74c3c"],
        autopct="%1.1f%%",
        startangle=140,
    )
    axes[0, 0].set_title("Overall Posture Quality")

    # [0,1] 長條圖：不良類型
    issue_list = []
    for item in df["Issues"].dropna():
        if item != "CALIBRATED_BASE":
            for p in item.split("/"):
                p = p.strip()
                if p:
                    issue_list.append(p)
    if issue_list:
        pd.Series(issue_list).value_counts().plot(
            kind="bar", ax=axes[0, 1], color="#f39c12"
        )
        axes[0, 1].tick_params(axis="x", rotation=30)
    else:
        axes[0, 1].text(0.5, 0.5, "No Issues Detected", ha="center", va="center")
    axes[0, 1].set_title("Issue Type Distribution")

    # [1,0] 雙Y軸：頸部角度（左）+ 高度差（右）
    ax_a = axes[1, 0]
    ax_y = ax_a.twinx()

    (l1,) = ax_a.plot(
        df_min["Minute"],
        df_min["neck_angle"],
        color="#3498db",
        linewidth=2,
        label="Neck Angle (°)",
    )
    ax_a.axhline(
        y=base_angle,
        color="#2980b9",
        linestyle=":",
        alpha=0.7,
        label=f"Base ({base_angle:.1f}°)",
    )
    ax_a.scatter([base_time], [base_angle], color="red", marker="*", s=150, zorder=5)
    ax_a.set_ylabel("Neck Angle (°)", color="#3498db")
    ax_a.tick_params(axis="y", labelcolor="#3498db")

    (l2,) = ax_y.plot(
        df_min["Minute"],
        df_min["curr_Y"],
        color="#e67e22",
        linewidth=2,
        linestyle="--",
        label="Height (curr_Y)",
    )
    ax_y.axhline(
        y=base_y_val,
        color="#d35400",
        linestyle=":",
        alpha=0.7,
        label=f"Base ({base_y_val:.4f})",
    )
    ax_y.set_ylabel("Height Diff (curr_Y)", color="#e67e22")
    ax_y.tick_params(axis="y", labelcolor="#e67e22")

    axes[1, 0].set_title("Trend: Neck Angle & Height Diff")
    axes[1, 0].set_xticks(df_min["Minute"][::step])
    axes[1, 0].tick_params(axis="x", rotation=45)
    axes[1, 0].grid(True, linestyle=":", alpha=0.4)
    axes[1, 0].legend(
        [l1, l2], [l1.get_label(), l2.get_label()], loc="upper left", fontsize=8
    )

    # [1,1] 久坐時間軸：Good / Bad 分布
    df["TimeNum"] = pd.to_datetime(df["Time"], format="%H:%M:%S", errors="coerce")
    good_df = df[df["Status"] == "GOOD POSTURE"]
    bad_df = df[df["Status"] == "BAD POSTURE"]
    axes[1, 1].scatter(
        good_df["Time"],
        [1] * len(good_df),
        color="#2ecc71",
        s=10,
        label="Good",
        alpha=0.6,
    )
    axes[1, 1].scatter(
        bad_df["Time"], [0] * len(bad_df), color="#e74c3c", s=10, label="Bad", alpha=0.6
    )
    axes[1, 1].set_yticks([0, 1])
    axes[1, 1].set_yticklabels(["Bad", "Good"])
    axes[1, 1].set_title("Posture Timeline")
    axes[1, 1].set_xticks(df["Time"][:: max(1, len(df) // 8)])
    axes[1, 1].tick_params(axis="x", rotation=45)
    axes[1, 1].legend(fontsize=8)
    axes[1, 1].grid(True, linestyle=":", alpha=0.4)

    plt.tight_layout()
    plt.savefig(temp_posture, dpi=120)
    plt.close()


# ── 圖二：眼睛相關（2x2）────────────────────────────────────
def _make_eye_chart(df, df_min):
    step = max(1, len(df_min) // 8)

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(
        f"Eye & Fatigue Analysis Report - {today}", fontsize=14, fontweight="bold"
    )

    # [0,0] 眨眼率趨勢
    if "BlinkRateMin" in df_min.columns:
        axes[0, 0].plot(
            df_min["Minute"], df_min["BlinkRateMin"], color="#1abc9c", linewidth=2
        )
        axes[0, 0].axhline(
            y=8, color="#e74c3c", linestyle=":", alpha=0.8, label="Warn < 8/min"
        )
        axes[0, 0].axhline(
            y=15, color="#2ecc71", linestyle=":", alpha=0.8, label="Normal 15/min"
        )
        axes[0, 0].set_ylabel("Blinks / min")
        axes[0, 0].legend(fontsize=8)
        axes[0, 0].set_xticks(df_min["Minute"][::step])
        axes[0, 0].tick_params(axis="x", rotation=45)
        axes[0, 0].grid(True, linestyle=":", alpha=0.4)
    else:
        axes[0, 0].text(0.5, 0.5, "No Blink Data", ha="center", va="center")
    axes[0, 0].set_title("Blink Rate Trend")

    # [0,1] 注視靜止秒數趨勢
    if "GazeStillSec" in df_min.columns:
        axes[0, 1].plot(
            df_min["Minute"], df_min["GazeStillSec"], color="#9b59b6", linewidth=2
        )
        axes[0, 1].axhline(
            y=20, color="#e74c3c", linestyle=":", alpha=0.8, label="Warn > 20s"
        )
        axes[0, 1].set_ylabel("Gaze Still (sec)")
        axes[0, 1].legend(fontsize=8)
        axes[0, 1].set_xticks(df_min["Minute"][::step])
        axes[0, 1].tick_params(axis="x", rotation=45)
        axes[0, 1].grid(True, linestyle=":", alpha=0.4)
    else:
        axes[0, 1].text(0.5, 0.5, "No Gaze Data", ha="center", va="center")
    axes[0, 1].set_title("Gaze Fixation Trend")

    # [1,0] 疲勞分數趨勢
    if "FatigueScore" in df_min.columns:
        scores = df_min["FatigueScore"]
        colors_map = scores.apply(
            lambda s: (
                "#2ecc71"
                if s < 25
                else "#f39c12" if s < 50 else "#e67e22" if s < 75 else "#e74c3c"
            )
        )
        axes[1, 0].bar(df_min["Minute"], scores, color=colors_map, width=0.8)
        axes[1, 0].axhline(
            y=25, color="#f39c12", linestyle=":", alpha=0.7, label="Mild (25)"
        )
        axes[1, 0].axhline(
            y=50, color="#e67e22", linestyle=":", alpha=0.7, label="Tired (50)"
        )
        axes[1, 0].axhline(
            y=75, color="#e74c3c", linestyle=":", alpha=0.7, label="Exhausted (75)"
        )
        axes[1, 0].set_ylabel("Fatigue Score")
        axes[1, 0].set_ylim(0, 100)
        axes[1, 0].legend(fontsize=8)
        axes[1, 0].set_xticks(df_min["Minute"][::step])
        axes[1, 0].tick_params(axis="x", rotation=45)
        axes[1, 0].grid(True, linestyle=":", alpha=0.4)
    else:
        axes[1, 0].text(0.5, 0.5, "No Fatigue Data", ha="center", va="center")
    axes[1, 0].set_title("Fatigue Score Trend")

    # [1,1] 疲勞等級圓餅圖
    if "FatigueLabel" in df.columns:
        label_counts = df["FatigueLabel"].value_counts()
        label_colors = {
            "Fresh": "#2ecc71",
            "Mild": "#f1c40f",
            "Tired": "#e67e22",
            "Exhausted": "#e74c3c",
        }
        labels = label_counts.index.tolist()
        clrs = [label_colors.get(l, "#95a5a6") for l in labels]
        axes[1, 1].pie(
            label_counts.values,
            labels=labels,
            colors=clrs,
            autopct="%1.1f%%",
            startangle=140,
        )
    else:
        axes[1, 1].text(0.5, 0.5, "No Fatigue Label Data", ha="center", va="center")
    axes[1, 1].set_title("Fatigue Level Distribution")

    plt.tight_layout()
    plt.savefig(temp_eye, dpi=120)
    plt.close()


# ── 主函式 ───────────────────────────────────────────────────
def export_to_excel_with_chart():
    if not os.path.exists(csv_file):
        print(f"找不到 CSV 檔案: {csv_file}")
        return

    df = pd.read_csv(csv_file, engine="python", on_bad_lines="skip")
    if df.empty:
        print("CSV 檔案內沒有數據。")
        return

    df["Minute"] = df["Time"].str[:5]
    df_min = df.groupby("Minute").mean(numeric_only=True).reset_index()

    _make_posture_chart(df, df_min)
    _make_eye_chart(df, df_min)

    with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
        # 原始資料
        df.to_excel(writer, sheet_name="Raw_Data", index=False)

        workbook = writer.book
        title_fmt = workbook.add_format(
            {"bold": True, "font_size": 14, "font_color": "#2c3e50"}
        )

        # 姿勢報告頁
        ws_posture = workbook.add_worksheet("Posture_Report")
        ws_posture.write("A1", f"Posture Report - {today}", title_fmt)
        ws_posture.insert_image("B3", temp_posture, {"x_scale": 0.75, "y_scale": 0.75})

        # 眼睛報告頁
        ws_eye = workbook.add_worksheet("Eye_Report")
        ws_eye.write("A1", f"Eye & Fatigue Report - {today}", title_fmt)
        ws_eye.insert_image("B3", temp_eye, {"x_scale": 0.75, "y_scale": 0.75})

    for f in [temp_posture, temp_eye]:
        if os.path.exists(f):
            os.remove(f)

    print(f"報告已輸出：{excel_file}（共 3 個分頁）")


if __name__ == "__main__":
    export_to_excel_with_chart()
