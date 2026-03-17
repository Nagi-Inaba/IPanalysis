import pandas as pd
from collections import Counter
import openpyxl
import sys 


# ワークブックをロード
fname = sys.argv[1]
wb = openpyxl.load_workbook(fname)
sheet_name = 'データ'

# データをpandasで読み込む
df = pd.read_excel(fname, sheet_name=sheet_name)

# 列名を自動で探す（筆頭出願人、 公報IPC）
column_applicant = None
column_publication_ipc = None

for col in df.columns:
    if '筆頭出願人' in col:
        column_applicant = col
    elif '公報IPC' in col:
        column_publication_ipc = col

if column_applicant is None or column_publication_ipc is None:
    print("「筆頭出願人」または「公報IPC」列が見つかりませんでした。")
else:
    # 出願人ごとの出願件数をカウント
    applicant_counts = Counter()
    ipc_counts_by_applicant = {}

    for idx, row in df.iterrows():
        # NaN チェックと文字列化を追加
        if pd.notna(row[column_applicant]):
            applicants = [applicant.strip() for applicant in str(row[column_applicant]).split(',')]
        else:
            applicants = []  # 出願人がNaNの場合は空リスト

        if pd.notna(row[column_publication_ipc]):
            ipc_classes = [ipc.strip() for ipc in str(row[column_publication_ipc]).split(',')]
        else:
            ipc_classes = []  # 公報IPCがNaNの場合は空リスト

        for applicant in applicants:
            applicant_counts[applicant] += 1
            if applicant not in ipc_counts_by_applicant:
                ipc_counts_by_applicant[applicant] = Counter()
            for ipc_class in ipc_classes:
                ipc_counts_by_applicant[applicant][ipc_class] += 1

    # IPCサブクラスごとの総出願件数をカウント
    total_ipc_counts = Counter()
    for ipc_counter in ipc_counts_by_applicant.values():
        total_ipc_counts.update(ipc_counter)

    # IPCサブクラスを総出願件数の多い順に並べ替える
    sorted_ipc_classes = [ipc for ipc, _ in total_ipc_counts.most_common()]

    # 結果をデータフレームに整理
    results = []
    for applicant, total_applications in applicant_counts.items():
        row = [applicant, total_applications]
        for ipc_class in sorted_ipc_classes:
            row.append(ipc_counts_by_applicant[applicant].get(ipc_class, 0))
        results.append(row)

    # ヘッダー作成
    headers = ['出願人名', '出願件数'] + sorted_ipc_classes

    # 結果をデータフレームに変換
    result_df = pd.DataFrame(results, columns=headers)

    # 出願件数の多い順に並べ替え
    result_df = result_df.sort_values(by='出願件数', ascending=False)

    # 既存のExcelファイルに新しいシート「公報IPC」を作成して保存
    with pd.ExcelWriter(fname, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        result_df.to_excel(writer, sheet_name='公報IPC', index=False)

    print("新しいシート「公報IPC」に結果を保存しました。")
