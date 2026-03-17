# IPanalysis -- IPC 増減率分析 Web アプリ

特許データ（xlsx/csv）から IPC 分類の経年増減率・出願人動向・技術マップを分析する Streamlit アプリ。

## 公開 URL

https://ipanalysis-webapp.streamlit.app/

## 技術スタック

- Python 3.8+
- Streamlit（Web UI）
- pandas, openpyxl（データ処理）
- Altair（可視化）
- pytest（テスト）

## コマンド

| コマンド | 説明 |
|---------|------|
| `pip install -r requirements.txt` | 依存インストール |
| `streamlit run app.py` | Web アプリ起動 |
| `python patent_analysis.py <file> <year>` | CLI 実行 |
| `pytest` | テスト実行 |

## ディレクトリ構成

| パス | 説明 |
|-----|------|
| `app.py` | Streamlit Web アプリ（1069行 -- リファクタリング対象） |
| `example_analysis.py` | 分析ロジック（17種の集計関数 + データクリーニング + 名寄せ辞書） |
| `patent_analysis.py` | IPC増減率計算（CLI/Web 両対応、openpyxl ベース） |
| `chart_utils.py` | グラフ PNG エクスポート（altair_saver 依存 -- 要更新） |
| `name_mapping.json` | 出願人名寄せ辞書（カスタマイズ可能） |
| `tests/` | pytest テスト（test_analysis.py, test_cleaning.py） |
| `excel_sample/` | サンプル Excel データ |
| `archive/` | 旧コード・アーカイブ |

## 対応データ形式

- J-PlatPat CSV/Excel（列名で自動判定）
- Questel CSV/Excel（列名で自動判定）
- 汎用 CSV/Excel（手動カラム設定）

## 分析機能（17種）

出願動向、IPC増減率、IPCサマリ、IPCメイングループ、IPC年次ヒートマップ、IPCツリーマップ、
出願人ランキング（筆頭/全体）、出願人増減率、出願人年次推移、出願人シェア、
参入退出分析、引用マップ、被引用出願一覧、
出願人xIPCヒートマップ、共同出願ネットワーク、
Fターム分布、Fターム年次ヒートマップ

## テスト

- 31 テスト（test_analysis.py: 15件、test_cleaning.py: 16件）
- 実行: `pytest`（pyproject.toml で testpaths=tests 設定済み）
- Python 3.14 環境にはpandas未インストール。テストは `C:/pythonapp/python.exe`（3.8）で実行可能

## Gotchas

- デプロイ先は Streamlit Community Cloud。`requirements.txt` が自動インストールされる
- `excel_sample/` に実データを含めないこと（機密・個人情報リスク）
- `.streamlit/secrets.toml` はリポジトリに含めないこと
- `.gitignore` で `*.csv` を除外済み（実データの誤コミット防止）
- app.py が 1069 行で 800 行上限を超過 -- サイドバー/CSS/セクション別にモジュール分割が必要
- chart_utils.py の altair_saver は非推奨 -- vl-convert-python への移行が必要
- example_analysis.py が 822 行で 800 行上限に近い -- 名寄せ辞書の外部化で軽量化可能
