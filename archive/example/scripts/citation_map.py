import pandas as pd
import openpyxl
from collections import defaultdict
import re
import sys 


# ワークブックをロード
fname = sys.argv[1]
wb = openpyxl.load_workbook(fname)
sheet = 'データ'  # ワークシート名
df = pd.read_excel(fname, sheet_name=sheet)

# 列名を自動で探す（更新出願人・権利者氏名と被引用回数）
column_applicant = None
column_citations = None

for col in df.columns:
    if '筆頭出願人' in col:
        column_applicant = col
    elif '被引用回数' in col:
        column_citations = col

if column_applicant is None or column_citations is None:
    print("「更新出願人・権利者氏名」または「被引用回数」列が見つかりませんでした。")
else:
    # 出願人ごとの引用回数と総出願件数の集計
    citation_data = defaultdict(list)
    applicant_counts = defaultdict(int)
    cited_applicant_counts = defaultdict(int)  # 一回でも引用された出願件数をカウント

    # データをカンマで分割し、各出願人に対して被引用回数を記録
    for index, row in df.iterrows():
        # 出願人名をカンマで分割
        applicants = [applicant.strip() for applicant in row[column_applicant].split(',')]

        # 被引用回数のフォーマットから数字を抽出、空白なら0として扱う
        citation_count = 0
        if pd.notna(row[column_citations]):
            citation_match = re.search(r'引用：(\d+)', row[column_citations])
            if citation_match:
                citation_count = int(citation_match.group(1))
        
        # すべての出願をカウントし、被引用回数があればそれも集計
        for applicant in applicants:
            citation_data[applicant].append(citation_count)
            applicant_counts[applicant] += 1  # 出願件数をカウント
            if citation_count > 0:
                cited_applicant_counts[applicant] += 1  # 一回でも引用された場合のカウント

    # 出願人ごとに、平均引用回数、最大引用回数、合計引用回数、総出願件数、引用された割合を計算
    result_data = []
    for applicant, citations in citation_data.items():
        avg_citation = sum(citations) / len(citations) if len(citations) > 0 else 0  # 平均引用回数
        max_citation = max(citations)  # 最大引用回数
        total_citations = sum(citations)  # 合計引用回数
        total_applications = applicant_counts[applicant]  # 総出願件数
        cited_applications = cited_applicant_counts[applicant]  # 一回でも引用された出願件数
        cited_percentage = (cited_applications / total_applications) if total_applications > 0 else 0  # 引用された割合（%）
        result_data.append([applicant, avg_citation, max_citation, total_citations, total_applications, cited_percentage])

    # データフレームに変換し、最大引用回数の多い順に並べ替え
    result_df = pd.DataFrame(result_data, columns=['出願人名', '平均引用回数', '最大引用回数', '合計引用回数', '出願件数', '引用された出願割合（%）'])
    result_df = result_df.sort_values(by='最大引用回数', ascending=False)

    # 既存のExcelファイルを開いて、新しいシート「被引用回数集計」に書き込む
    with pd.ExcelWriter(fname, mode='a', engine='openpyxl') as writer:
        result_df.to_excel(writer, sheet_name='被引用回数集計', index=False)

    print(f"結果を新しいシート「被引用回数集計」に保存しました。")
