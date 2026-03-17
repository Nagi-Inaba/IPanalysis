# IPanalysis -- IP Analysis Studio

特許データ（Excel/CSV）から IPC 分類の経年増減率・出願人動向・技術マップを分析する Streamlit Web アプリ。

## 公開 URL

**https://ipanalysis-webapp.streamlit.app/**

## 主な機能

| カテゴリ | 分析機能 |
|---------|---------|
| 出願動向 | 出願件数の年次推移 |
| IPC 分析 | IPC 増減率（10年/5年比較）、IPC サマリ、IPC メイングループ別、IPC 年次ヒートマップ、IPC ツリーマップ |
| 出願人分析 | 出願人ランキング（筆頭/全体）、出願人増減率、出願人年次推移、出願人シェア、参入・退出分析 |
| クロス分析 | 出願人 x IPC ヒートマップ、共同出願ネットワーク |
| 引用分析 | 引用マップ、被引用出願一覧 |
| F ターム | F ターム分布、F ターム年次ヒートマップ |
| データ対応 | J-PlatPat / Questel / 汎用 CSV 自動検出 |
| 名寄せ | 出願人名の自動正規化（150+ ルール、カスタム辞書対応） |

## 構成

| パス | 説明 |
|-----|------|
| `app.py` | Streamlit Web アプリ（メイン UI） |
| `example_analysis.py` | 分析ロジック（17 種の集計関数 + データクリーニング） |
| `patent_analysis.py` | IPC 増減率計算（CLI / Web 両対応、openpyxl ベース） |
| `chart_utils.py` | グラフ PNG エクスポートユーティリティ |
| `name_mapping.json` | 出願人名寄せ辞書（カスタマイズ可能） |
| `tests/` | pytest テスト |
| `excel_sample/` | サンプル Excel データ |

## セットアップ

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Web アプリ実行

```bash
streamlit run app.py
```

ブラウザで表示された画面から `.xlsx` または `.csv` をアップロードし、基準年などを設定して分析します。

実行後は:
- 画面上で集計結果・グラフを確認
- 加工済み Excel（結果シート追加済み）をダウンロード
- CSV をダウンロード

## CLI 実行

```bash
python patent_analysis.py 入力ファイル.xlsx 2015
```

主なオプション:

```bash
python patent_analysis.py 入力ファイル.xlsx 2015 \
  --year-range 10 \
  --source-sheet データ \
  --ipc-column 公報IPC \
  --year-column 出願年
```

指定しない場合、出力ファイルは `*_analysis.xlsx` になります。

## テスト

```bash
pytest
```

## 対応データ形式

| 形式 | ソース | 自動検出 |
|------|--------|---------|
| J-PlatPat CSV/Excel | 特許情報プラットフォーム | 列名で自動判定 |
| Questel CSV/Excel | Questel Orbit | 列名で自動判定 |
| 汎用 CSV/Excel | その他 | 手動カラム設定 |

アップロード後、データ形式が自動検出され、列マッピングのデフォルト値が設定されます。
汎用形式の場合は手動でカラムを紐付けてください。

---

## Streamlit Community Cloud へのデプロイ

### 前提

- GitHub アカウントを持っていること
- このリポジトリが GitHub 上に公開されていること

### 手順

1. **GitHub にリポジトリを作成してプッシュする**

   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/<ユーザー名>/IPanalysis.git
   git push -u origin main
   ```

2. **Streamlit Community Cloud にログイン**

   https://share.streamlit.io にアクセスし、GitHub アカウントでログイン。

3. **アプリを新規デプロイ**

   - "New app" をクリック
   - Repository: `<ユーザー名>/IPanalysis`
   - Branch: `main`
   - Main file path: `app.py`
   - "Deploy!" をクリック

4. **依存関係は自動インストール**

   `requirements.txt` の内容が自動的にインストールされます。

### 注意事項

- `excel_sample/` 内の実データ Excel ファイルはリポジトリに含めないことを推奨（機密・個人情報リスク）
- PNG エクスポート機能は `vl-convert-python` で動作（Streamlit Cloud 環境では確認が必要）
- `.streamlit/secrets.toml` はリポジトリに含めないこと
