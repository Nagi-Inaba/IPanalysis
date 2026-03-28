# IPanalysis -- 特許分類増減率分析 Web アプリ

特許データ（xlsx/csv）から特許分類（IPC/FI/Fターム）の経年増減率・出願人動向・技術マップを分析する Streamlit アプリ。

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
| `charts_advanced.py` | 高度分析グラフ（共起ネットワーク、技術ライフサイクル、出願戦略マップ等） |
| `analysis_advanced.py` | 高度分析ロジック（共起分析、技術ライフサイクル、ポートフォリオ分析等） |
| `cached_agg.py` | Streamlit キャッシュ付き集計ラッパー（70行） |
| `constants.py` | IPC/FI/Fターム粒度定数（44行） |
| `example_analysis.py` | 分析ロジック（17種の集計関数 + データクリーニング + 名寄せ辞書） |
| `patent_analysis.py` | 特許分類増減率計算（CLI/Web 両対応、openpyxl ベース） |
| `chart_utils.py` | グラフ PNG エクスポート（altair_saver 依存 -- 要更新） |
| `name_mapping.json` | 出願人名寄せ辞書（カスタマイズ可能） |
| `tests/` | pytest テスト（test_analysis.py, test_cleaning.py, test_advanced_analysis.py） |
| `tests/e2e/` | Playwright E2E テスト（conftest.py, test_app.py） |
| `excel_sample/` | サンプル Excel データ |
| `archive/` | 旧コード・アーカイブ |
| `slides/` | LTプレゼン（HTML + PPTX + 構成md）。`python slides/generate_pptx.py` で再生成（python-pptx, qrcode[pil] 必要） |

## 対応データ形式

- J-PlatPat CSV/Excel（列名で自動判定）
- Questel CSV/Excel（列名で自動判定）
- 汎用 CSV/Excel（手動カラム設定）

## 分析機能（17種 + 高度分析6種）

出願動向、特許分類増減率、特許分類集計、筆頭分類メイングループ、分類別年次ヒートマップ、分類ツリーマップ、
出願人ランキング（筆頭/全体）、出願人増減率、出願人年次推移、出願人シェア、
参入退出分析、引用マップ、被引用出願一覧、
出願人x分類ヒートマップ、共同出願ネットワーク、
Fターム分布、Fターム年次ヒートマップ

高度分析: 分類共起ネットワーク、技術ライフサイクル、技術ポートフォリオマップ、出願戦略マップ、技術融合分析、ホワイトスペース分析

## テスト

- ユニット: 31テスト（test_analysis.py: 15件、test_cleaning.py: 16件）+ test_advanced_analysis.py
- E2E: 3テスト（Playwright -- `pytest tests/e2e -m e2e`）
- 実行: `pytest`（pyproject.toml で testpaths=tests 設定済み）
- E2E実行: Python 3.12 + streamlit + playwright が必要。`$HOME/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/e2e -m e2e`
- Python 3.14 環境にはpandas未インストール。テストは `C:/pythonapp/python.exe`（3.8）で実行可能

## Gotchas

- デプロイ先は Streamlit Community Cloud。`requirements.txt` が自動インストールされる
- `excel_sample/` に実データを含めないこと（機密・個人情報リスク）
- `.streamlit/secrets.toml` はリポジトリに含めないこと
- `.gitignore` で `*.csv` を除外済み（実データの誤コミット防止）
- app.py を 1069→455 行にリファクタリング済み（charts.py, cached_agg.py, constants.py に分割）
- chart_utils.py の altair_saver は非推奨 -- vl-convert-python への移行が必要
- example_analysis.py が 822 行で 800 行上限に近い -- 名寄せ辞書の外部化で軽量化可能
- UI表示は「特許分類」に統一済みだが、内部カラム名（constants.py IPC_LEVEL_COL / example_analysis.py COL_IPC）は「IPC」のまま。charts.py では `.rename(columns={"IPC": classification})` でUI表示時にリネームしている
- charts_advanced.py の共起分析は生の複数分類カラム（`公報IPC`等）が必要。`筆頭IPCサブクラス`（単一値）を渡すと共起が発生しない
- E2E テストはサンプルデータフローを使用。ファイルアップロードは Streamlit の制約上テスト困難
- charts_advanced.py は cached_agg.py のキャッシュラッパー経由で分析関数を呼び出す。直接 import しない
