# Memory Server MCP - macOS アプリ化ガイド

このプロジェクトをmacOSでダブルクリックで動くアプリにする方法を説明します。

## 方法1: PyInstaller を使ったスタンドアロンアプリ（推奨）

### セットアップ
```bash
# 自動セットアップスクリプトを実行
./setup_app.sh
```

または手動で：

```bash
# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate

# 依存関係をインストール
pip install fastapi uvicorn fastmcp pydantic pyinstaller

# アプリをビルド
python3 build_app.py
```

### 使用方法
1. `dist/MemoryServerMCP/MemoryServerMCP` をダブルクリック
2. ブラウザで `http://localhost:8000` にアクセス

## 方法2: GUIランチャー（簡単）

### 起動
```bash
python3 launcher.py
```

### 特徴
- シンプルなGUI
- サーバーの開始/停止ボタン
- ログ表示
- ブラウザ自動起動

## 方法3: Automator アプリ

### セットアップ
```bash
python3 create_automator_app.py
```

### Automator での作成手順
1. Automator.app を開く
2. 「アプリケーション」を選択
3. 「シェルスクリプトを実行」をドラッグ
4. 生成された `launch_memory_server.sh` のパスを入力
5. 「Memory Server MCP.app」として保存

## 方法4: AppleScript アプリ

### 作成手順
1. `python3 create_automator_app.py` を実行
2. Script Editor で `Memory Server MCP.scpt` を開く
3. 「ファイル」→「書き出す」→「アプリケーション」を選択
4. 保存したアプリをダブルクリックで起動

## トラブルシューティング

### Python環境の問題
```bash
# Homebrewでpython3をインストール
brew install python3

# または公式サイトからダウンロード
# https://www.python.org/downloads/
```

### 権限の問題
```bash
# スクリプトに実行権限を付与
chmod +x setup_app.sh
chmod +x launch_memory_server.sh
```

### ポートの競合
- デフォルトポート8000が使用中の場合
- `main.py` の `Config.PORT` を変更

### セキュリティ警告
- macOSで「開発元が未確認」の警告が出た場合
- システム環境設定 → セキュリティとプライバシー → 「このまま開く」

## 配布用パッケージの作成

### DMGファイルの作成
```bash
# create-dmgをインストール
brew install create-dmg

# DMGファイルを作成
create-dmg \
  --volname "Memory Server MCP" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 100 \
  --app-drop-link 425 120 \
  "Memory-Server-MCP.dmg" \
  "dist/MemoryServerMCP/"
```

## 推奨構成

最も使いやすい構成：

1. **開発時**: `python3 launcher.py` でGUIランチャーを使用
2. **配布時**: PyInstallerでビルドしたアプリを使用
3. **簡単配布**: Automator アプリとして作成

## 注意事項

- 初回起動時は依存関係のインストールが必要
- SQLiteデータベース（memory.db）は自動作成される
- ログファイル（memory_server.log）も自動作成される
- ポート8000が他のアプリで使用されていないことを確認

## サポート

問題が発生した場合：
1. ログファイル（memory_server.log）を確認
2. ターミナルで `python3 main.py` を直接実行してエラーを確認
3. 仮想環境の再作成を試す