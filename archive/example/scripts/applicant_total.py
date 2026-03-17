import pandas as pd
import openpyxl
from collections import Counter
from openpyxl import load_workbook
import sys 


# ワークブックをロード
fname = sys.argv[1]
wb = openpyxl.load_workbook(fname)
sheet = 'データ'  # ワークシート名
df = pd.read_excel(fname, sheet_name=sheet)

# 範囲を指定
start_year = int(sys.argv[2])
end_year = int(sys.argv[3])

# 列名を自動で探す（出願年と更新出願人・権利者氏名）
column_applicant = None
column_year = None

for col in df.columns:
    if '更新出願人・権利者氏名' in col:
        column_applicant = col
    elif '出願年' in col:
        column_year = col

if column_applicant is None or column_year is None:
    print("「更新出願人・権利者氏名」または「出願年」列が見つかりませんでした。")
else:
    # 出願年の範囲でフィルタリング
    filtered_df = df[(df[column_year] >= start_year) & (df[column_year] <= end_year)]

    # 出願人名をカンマで分割し、同一セル内での重複を取り除き、すべての出願人をリスト化
    all_applicants = []
    for entry in filtered_df[column_applicant].dropna():
        # 出願人名を分割して重複を削除（set()で重複排除）
        applicants = set([applicant.strip() for applicant in entry.split(',')])
        all_applicants.extend(applicants)

    # 出願人ごとのカウントを取得
    applicant_counts = Counter(all_applicants)

    # 結果をデータフレームに変換し、登場回数の多い順に並べ替え
    output_df = pd.DataFrame(applicant_counts.items(), columns=['出願人名', '出願件数'])
    output_df = output_df.sort_values(by='出願件数', ascending=False)

    # 既存のExcelファイルを開いて、新しいシート「総出願人カウント」に書き込む
    with pd.ExcelWriter(fname, mode='a', engine='openpyxl') as writer:
        output_df.to_excel(writer, sheet_name='総出願人カウント', index=False)

    print(f"結果を新しいシート「総出願人カウント」に保存しました。")
