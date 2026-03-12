# IPanalysis

`ipc_growth.py` の処理をベースに、IPC増減率分析を Web アプリ化したプロジェクトです。

## 構成

- `patent_analysis.py`: 集計ロジック（CLI / Web 両対応）
- `ipc_growth.py`: CLIエントリポイント
- `app.py`: Streamlit Webアプリ

## セットアップ

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Webアプリ実行

```bash
streamlit run app.py
```

ブラウザで表示された画面から `.xlsx` をアップロードし、基準年などを設定して分析します。  
実行後は:

- 画面上で集計結果を確認
- 加工済みExcel（結果シート追加済み）をダウンロード
- CSVをダウンロード

## CLI実行

```bash
python ipc_growth.py 入力ファイル.xlsx 2015
```

主なオプション:

```bash
python ipc_growth.py 入力ファイル.xlsx 2015 --year-range 10 --source-sheet データ --ipc-column 公報IPC --year-column 出願年
```

指定しない場合、出力ファイルは `*_analysis.xlsx` になります。

---

## Streamlit Community Cloud へのデプロイ

### 前提

- GitHub アカウントを持っていること
- このリポジトリが GitHub 上に公開（または Streamlit Community Cloud と連携した）リポジトリであること

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

   <https://share.streamlit.io> にアクセスし、GitHub アカウントでログイン。

3. **アプリを新規デプロイ**

   - "New app" をクリック
   - Repository: `<ユーザー名>/IPanalysis`
   - Branch: `main`
   - Main file path: `app.py`
   - "Deploy!" をクリック

4. **依存関係は自動インストール**

   `requirements.txt` の内容が自動的にインストールされます。

### 注意事項

- `excel_sample/非水電解質電池.xlsx` など実データの Excel ファイルはリポジトリに含めないことを推奨します。
  含める場合は機密・個人情報が無いことを必ず確認してください。
- PNG エクスポート機能（グラフのダウンロード）は `vl-convert-python` で動作します。
  Community Cloud の無料プランで動作確認をしてください。
- シークレット情報（APIキー等）が必要な場合は Streamlit の Secrets 管理機能を使用します
  （`.streamlit/secrets.toml` はリポジトリに含めないこと）。
