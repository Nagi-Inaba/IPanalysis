# archive/

このディレクトリには、`app.py`（Streamlit アプリ）で代替済みのレガシーファイルを保管しています。

## 内容

| パス | 説明 |
|------|------|
| `example/scripts/` | 旧スタンドアロン Python スクリプト群（12ファイル） |
| `example/dist/Patent.exe` | PyInstaller でビルドした旧 GUI 実行ファイル |
| `example/build/` | PyInstaller ビルド成果物 |

## 現在の使い方

```bash
# Streamlit アプリを起動する
streamlit run app.py
```

レガシースクリプトは機能的に `app.py` に統合されています。
参照目的でのみ保管しています。
