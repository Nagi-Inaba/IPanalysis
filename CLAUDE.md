# IPanalysis -- IPC 増減率分析 Web アプリ

特許データ（xlsx/csv）から IPC 分類の経年増減率・出願人動向・技術マップを分析する Streamlit アプリ。

## 所属組織: PatentScope（子会社）

このプロジェクトは PatentScope 子会社が管轄する。作業開始時に以下を読み込むこと:

- **子会社本部**: `C:/Users/Nagi/.company/subsidiaries/patentscope/CLAUDE.md`
- **スプリント**: `C:/Users/Nagi/.company/subsidiaries/patentscope/todos/current-sprint.md`
- **統合計画**: `C:/Users/Nagi/.company/subsidiaries/patentscope/engineering/2026-03-17-unified-platform-plan.md`
- **調査手法**: `C:/Users/Nagi/.company/subsidiaries/patentscope/research/2026-03-17-research-methodology.md`
- **親会社PM**: `C:/Users/Nagi/.company/pm/projects/2026-03-12-ipanalysis.md`

チーム: 特許アナリスト / データエンジニア / 可視化スペシャリスト / UI・UXデザイナー
姉妹プロジェクト: 特許分析apollo (`C:/Users/Nagi/OneDrive/ドキュメント/特許分析apollo/`)

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
| `app.py` | Streamlit Web アプリ（455行 -- Step 1/2 + メインフロー） |
| `charts.py` | Step 3 グラフ描画（555行 -- 15種のチャート + 設定UI） |
| `cached_agg.py` | Streamlit キャッシュ付き集計ラッパー（70行） |
| `constants.py` | IPC/FI/Fターム粒度定数（44行） |
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
- app.py を 1069→455 行にリファクタリング済み（charts.py, cached_agg.py, constants.py に分割）
- chart_utils.py の altair_saver は非推奨 -- vl-convert-python への移行が必要
- example_analysis.py が 822 行で 800 行上限に近い -- 名寄せ辞書の外部化で軽量化可能
