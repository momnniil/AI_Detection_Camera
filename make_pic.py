# import pandas as pd
# import matplotlib.pyplot as plt
# import os

# # 設定路徑
# csv_file = os.path.join("posture_report_20260312.csv")
# excel_file = os.path.join("Posture_Analysis_Report.xlsx")
# temp_img = "temp_chart.png"


# def export_to_excel_with_chart():
#     if not os.path.exists(csv_file):
#         print("找不到 CSV 檔案")
#         return

#     # 1. 讀取數據
#     df = pd.read_csv(csv_file, engine='python')

#     # 2. 生成與先前邏輯相同的圖表並儲存為圖片
#     fig, axes = plt.subplots(1, 3, figsize=(18, 6))

#     # --- 圓餅圖 ---
#     status_counts = df['Status'].value_counts()
#     axes[0].pie([status_counts.get('GOOD POSTURE', 0), status_counts.get('BAD POSTURE', 0)],
#                 labels=['Good', 'Bad'], colors=['#2ecc71', '#e74c3c'], autopct='%1.1f%%')
#     axes[0].set_title('Overall Status')

#     # --- 趨勢圖 ---
 
#     df['Minute'] = df['Time'].str[:5]
#     df_min = df.groupby('Minute').mean(numeric_only=True)
#     df_min['Status'] = df.groupby('Minute')['Status'].first()


#     # --- 繪製趨勢圖 (axes[1]) ---
#     # 第一條線：頸部角度 (左側 Y 軸)
#     line1 = axes[1].plot(df_min['Minute'], df_min['neck_angle'],
#                          color='#3498db', linewidth=2, label='Neck Angle (Deg)')
#     axes[1].set_ylabel('Neck Angle (Degrees)', color='#3498db')
#     axes[1].tick_params(axis='y', labelcolor='#3498db')

#     # 創建雙 Y 軸
#     ax1_twin = axes[1].twinx()

#     # 第二條線：高度差 curr_Y (右側 Y 軸)
#     line2 = ax1_twin.plot(df_min['Minute'], df_min['curr_Y'],
#                           color='#e67e22', linewidth=2, linestyle='--', label='Height Diff (curr_Y)')
#     ax1_twin.set_ylabel('Height Diff (curr_Y)', color='#e67e22')
#     ax1_twin.tick_params(axis='y', labelcolor='#e67e22')

#     # 設定標題與 X 軸
#     axes[1].set_title('Fatigue Trend: Neck & Height')
#     step = max(1, len(df_min) // 8)
#     axes[1].set_xticks(df_min['Minute'][::step])
#     axes[1].tick_params(axis='x', rotation=45)
#     # 合併
#     lines = line1 + line2
#     labels = [l.get_label() for l in lines]
#     axes[1].legend(lines, labels, loc='upper left')
    
#     # --- 不良類型分析 ---
#     issue_list = []
#     for item in df['Issues'].dropna():
#         for p in item.split('/'):
#             p = p.strip()
#             if p == 'Head Drop':
#                 p = 'Hunching'
#             if p:
#                 issue_list.append(p)
#     if issue_list:
#         pd.Series(issue_list).value_counts().plot(
#             kind='bar', ax=axes[2], color='#f39c12')
#     axes[2].set_title('Issue Type Analysis')

#     plt.tight_layout()
#     plt.savefig(temp_img)  # 暫存圖片
#     plt.close()

#     # 3. 將數據與圖片寫入 Excel
#     with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
#         # 寫入原始數據頁面
#         df.to_excel(writer, sheet_name='Data_Source', index=False)

#         # 創建分析報告頁面
#         workbook = writer.book
#         worksheet = workbook.add_worksheet('Analysis_Report')
#         writer.sheets['Analysis_Report'] = worksheet

#         # 在 Excel 中寫入文字標題
#         header_format = workbook.add_format(
#             {'bold': True, 'font_size': 14, 'font_color': 'blue'})
#         worksheet.write(
#             'A1', 'AI Posture Detection Daily Report - 2026/03/12', header_format)

#         # 鑲嵌圖片 (從 B3 儲存格開始放)
#         worksheet.insert_image(
#             'B3', temp_img, {'x_scale': 0.8, 'y_scale': 0.8})

#     # 4. 清理暫存圖檔
#     if os.path.exists(temp_img):
#         os.remove(temp_img)

#     print(f"Excel 報表已生成：{excel_file}")


# if __name__ == "__main__":
#     export_to_excel_with_chart()


import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

# 設定路徑 (建議使用動態日期)
today = datetime.now().strftime("%Y%m%d")
csv_file = f"posture_report_{today}.csv"
excel_file = f"Posture_Analysis_Report_{today}.xlsx"
temp_img = "temp_combined_charts.png"


def export_to_excel_with_chart():
    if not os.path.exists(csv_file):
        print(f"找不到 CSV 檔案: {csv_file}")
        return

    # 1. 讀取數據
    df = pd.read_csv(csv_file, engine='python')
    if df.empty:
        print("CSV 檔案內沒有數據。")
        return

    # --- 數據預處理 (取得每分鐘平均值) ---
    df['Minute'] = df['Time'].str[:5]
    # 計算每分鐘數值平均
    df_min = df.groupby('Minute').mean(numeric_only=True).reset_index()

    # 提取基準值 (抓取 Issues 為 CALIBRATED_BASE 的那一筆)
    base_data = df[df['Issues'] == 'CALIBRATED_BASE']
    if not base_data.empty:
        last_base = base_data.iloc[-1]
        base_angle = float(last_base['neck_angle'])
        base_y_val = float(last_base['curr_Y'])
        base_time_label = last_base['Time'][:5]
    else:
        # 防呆：若沒校準標籤則取第一筆
        base_angle = df['neck_angle'].iloc[0]
        base_y_val = df['curr_Y'].iloc[0]
        base_time_label = df['Minute'].iloc[0]

    # 2. 生成圖表 (2x2 佈局)
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))

    # --- [0,0] 圓餅圖：整體狀態 ---
    status_counts = df['Status'].value_counts()
    axes[0, 0].pie([status_counts.get('GOOD POSTURE', 0), status_counts.get('BAD POSTURE', 0)],
                   labels=['Good', 'Bad'], colors=['#2ecc71', '#e74c3c'], autopct='%1.1f%%', startangle=140)
    axes[0, 0].set_title('Overall Posture Quality')

    # --- [0, 1] 長條圖：不良類型分析 ---
    # 排除校準標籤後的 Issues 統計
    issue_list = []
    for item in df['Issues'].dropna():
        if item != 'CALIBRATED_BASE':
            for p in item.split('/'):
                p = p.strip()
                if p:
                    issue_list.append(p)

    if issue_list:
        pd.Series(issue_list).value_counts().plot(
            kind='bar', ax=axes[0, 1], color='#f39c12')
        axes[0, 1].set_title('Issue Type Distribution')
        axes[0, 1].tick_params(axis='x', rotation=30)
    else:
        axes[0, 1].text(0.5, 0.5, 'No Issues Detected', ha='center')

    # --- [1, 0] 折線圖：頸部角度趨勢 ---
    axes[1, 0].plot(df_min['Minute'], df_min['neck_angle'],
                    color='#3498db', linewidth=2, label='Avg Angle')
    axes[1, 0].axhline(y=base_angle, color='#2980b9', linestyle=':',
                       alpha=0.7, label=f'Base ({base_angle:.1f})')
    axes[1, 0].scatter(base_time_label, base_angle, color='red',
                       marker='*', s=150, zorder=5, label='Calibrated')
    axes[1, 0].set_title('Trend: Neck Angle (Degrees)')
    axes[1, 0].set_ylabel('Degrees')
    axes[1, 0].legend(loc='lower right')

    # --- [1, 1] 折線圖：高度差趨勢 ---
    axes[1, 1].plot(df_min['Minute'], df_min['curr_Y'],
                    color='#e67e22', linewidth=2, label='Avg Height')
    axes[1, 1].axhline(y=base_y_val, color='#d35400', linestyle=':',
                       alpha=0.7, label=f'Base ({base_y_val:.4f})')
    axes[1, 1].scatter(base_time_label, base_y_val,
                       color='red', marker='*', s=150, zorder=5)
    axes[1, 1].set_title('Trend: Body Height (curr_Y)')
    axes[1, 1].set_ylabel('Height Value')
    axes[1, 1].legend(loc='lower right')

    # 優化底部兩張圖的 X 軸
    step = max(1, len(df_min) // 8)
    for ax in [axes[1, 0], axes[1, 1]]:
        ax.set_xticks(df_min['Minute'][::step])
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, linestyle=':', alpha=0.5)

    plt.tight_layout()
    plt.savefig(temp_img)
    plt.close()

    # 3. 將數據與圖片寫入 Excel
    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
        # A. 數據分頁
        df.to_excel(writer, sheet_name='Raw_Data', index=False)

        # B. 報告分頁
        workbook = writer.book
        worksheet = workbook.add_worksheet('Analysis_Report')

        # 設定標題格式
        title_fmt = workbook.add_format(
            {'bold': True, 'font_size': 16, 'font_color': '#2c3e50'})
        worksheet.write(
            'A1', f'AI Posture Guardian Report - {today}', title_fmt)

        # 插入圖片
        worksheet.insert_image(
            'B3', temp_img, {'x_scale': 0.75, 'y_scale': 0.75})

    # 4. 清理
    if os.path.exists(temp_img):
        os.remove(temp_img)



if __name__ == "__main__":
    export_to_excel_with_chart()
