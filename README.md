# Memory Server MCP

個人用メモリサーバー - Cursor/Claude統合用のMCP（Model Context Protocol）準拠サーバー

## 概要

このプロジェクトは、長時間の会話におけるコンテキスト喪失問題を解決するため、MCP（Model Context Protocol）を通じてCursor/Claudeと統合する個人用メモリサーバーです。LLMに長期記憶機能を提供し、保存された情報を能動的に参照・活用することで、より一貫性があり効率的な開発支援を実現します。

### 🚀 プロジェクト完成状況

**✅ 完全完成済み (2025-01-01)**
- 3サーバー分離アーキテクチャの実装完了
- WebUI統合の実装完了
- EXE版配布パッケージ作成完了
- 全機能テスト完了
- 複数Cursor接続対応完了

### 🏗️ アーキテクチャ

本プロジェクトは3つの独立したサーバーで構成される分散アーキテクチャを採用しています：

1. **MCP Server** (ポート8000) - MCPプロトコル専用サーバー
   - Cursor/Claude等のAIツールとの通信
   - stdio経由のMCPプロトコル処理

2. **WebUI Server** (ポート8001) - Web インターフェース
   - ブラウザベースのメモリ管理UI
   - API Serverへのプロキシ機能

3. **API Server** (ポート8002) - REST API専用サーバー
   - HTTP経由のメモリ操作API
   - WebUIおよび外部アプリケーションからの利用

## 主な機能

### 📋 コア機能
- **メモリエントリ管理**: テキスト情報をタグ、キーワード、要約と共に保存
- **高速検索機能**: キーワードやタグによる柔軟な検索
- **MCP統合**: LLMが直接アクセス可能なツール群
- **REST API**: HTTP経由でのメモリ操作
- **Web UI**: ブラウザベースの直感的な管理インターフェース

### 🔧 技術的特徴
- **3サーバー分離アーキテクチャ**: 機能別に分離された堅牢な設計
- **軽量設計**: SQLiteベースの単一ファイルデータベース
- **ローカル実行**: 外部依存なしの完全ローカル動作
- **ポータブル**: 単一ファイルデータベースによる簡単な移行
- **安定性重視**: 速度よりも信頼性を優先した設計
- **EXE配布対応**: PyInstallerによる単一実行ファイル化
- **複数接続対応**: 複数Cursorインスタンスからの同時接続をサポート

## 📦 インストールと起動方法

### 🎯 推奨方法：EXE版の使用

**最も簡単で推奨される方法です**

1. `dist/MemoryServerMCP.exe` (42MB) を実行
2. 自動的に3つのサーバーが起動
3. すぐに利用開始可能

**利用可能なエンドポイント**：
- **WebUI**: http://localhost:8001
- **REST API**: http://localhost:8002 
- **Health Check**: http://localhost:8002/health
- **MCP Protocol**: stdio経由（Cursor/Claude用）

### 🐍 開発者向け：Python版の使用

#### 必要な環境

- **Python**: 3.8以上（推奨: 3.9以上）
- **pip**: Pythonパッケージマネージャー
- **OS**: Windows、macOS、Linux（クロスプラットフォーム対応）

### セットアップ手順

#### 1. プロジェクトのダウンロード

```bash
# GitHubからクローン（または手動でファイルをダウンロード）
git clone <repository-url>
cd memory-server-mcp
```

#### 2. 仮想環境の作成（推奨）

```bash
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

#### 3. 依存関係のインストール

```bash
# 必要なパッケージをインストール
pip install -r requirements.txt
```

#### 4. サーバー起動とテスト

```bash
# 3つのサーバーを同時起動（初回実行時にデータベースが自動作成されます）
python main.py
```

正常に起動すると、以下のようなメッセージが表示されます：
```
INFO - Memory Server starting...
INFO - Database initialized at: memory.db
INFO - 🔧 MCP Server: http://localhost:8000
INFO - 🌐 WebUI Server: http://localhost:8001  
INFO - 🚀 API Server: http://localhost:8002
INFO - All servers started successfully!
```

#### 5. 動作確認

各サーバーの動作を確認：

```bash
# MCP Server（メイン）のヘルスチェック
curl http://localhost:8000/health

# API Server の動作確認
curl http://localhost:8002/health

# WebUI にブラウザでアクセス
# http://localhost:8001
```

## 🚀 使用方法

### サーバー起動

#### 通常起動（3サーバー同時起動）
```bash
# EXE版
./dist/MemoryServerMCP.exe

# Python版
python main.py
```

サーバーが正常に起動すると、以下の機能が利用可能になります：

**🔧 MCP Server (ポート8000)**:
- LLMからのツール呼び出しを受け付け
- stdio経由のMCPプロトコル処理

**🌐 WebUI Server (ポート8001)**:
- ブラウザベースのメモリ管理画面
- 直感的なCRUD操作インターフェース
- API Serverへのプロキシ機能

**🚀 API Server (ポート8002)**:
- REST API によるメモリ操作
- 外部アプリケーションとの連携
- 高速なJSON レスポンス

#### Python版の個別起動オプション
```bash
# REST APIのみ起動（開発・テスト用）
python main.py --api-only

# 設定確認モード
python main.py --check-config
```

### 🔗 Cursor/ClaudeでのMCP設定

#### 1. MCP設定ファイルの作成

**EXE版使用の場合** (推奨):
```json
{
  "mcpServers": {
    "memory-server": {
      "command": "path/to/MemoryServerMCP.exe",
      "args": [],
      "env": {
        "MEMORY_LOG_LEVEL": "WARNING"
      },
      "disabled": false,
      "autoApprove": [
        "add_note_to_memory",
        "search_memory",
        "get_project_rules",
        "list_all_memories"
      ]
    }
  }
}
```

**Python版使用の場合**:
```json
{
  "mcpServers": {
    "memory-server": {
      "command": "python",
      "args": ["path/to/your/main.py"],
      "cwd": "path/to/your/memory-server-mcp",
      "env": {
        "MEMORY_SERVER_HOST": "localhost",
        "MEMORY_SERVER_PORT": "8000",
        "MEMORY_LOG_LEVEL": "INFO"
      },
      "disabled": false,
      "autoApprove": [
        "add_note_to_memory",
        "search_memory", 
        "get_project_rules",
        "list_all_memories",
        "update_memory_entry",
        "delete_memory_entry"
      ]
    }
  }
}
```

#### 2. 設定の確認

Cursor IDEで以下を確認：
1. コマンドパレット（Cmd/Ctrl+Shift+P）を開く
2. "MCP" で検索
3. "MCP Server View" でサーバーの状態を確認
4. 緑色のステータスが表示されれば接続成功

### 環境変数による設定

以下の環境変数で設定をカスタマイズできます：

```bash
# サーバー設定
export MEMORY_SERVER_HOST=localhost
export MEMORY_SERVER_PORT=8000

# データベース設定
export MEMORY_DB_PATH=memory.db

# ログ設定
export MEMORY_LOG_LEVEL=INFO
export MEMORY_LOG_FILE=memory_server.log

# 検索設定
export MEMORY_MAX_SEARCH_RESULTS=100
```

### MCPツール

LLMから利用可能なツール：

1. **add_note_to_memory**: メモリにノートを追加
2. **search_memory**: キーワードまたはタグでメモリを検索
3. **update_memory_entry**: 既存のメモリエントリを更新
4. **delete_memory_entry**: メモリエントリを削除
5. **list_all_memories**: すべてのメモリエントリを一覧表示
6. **get_project_rules**: プロジェクトルールタグ付きメモリを取得

### 🌐 Web UI の使用 (推奨)

**アクセス方法**: http://localhost:8001

#### 主な機能
- **📝 メモリエントリ作成**: 直感的なフォーム入力
- **📊 一覧表示**: タグやキーワードで見やすく整理
- **🔍 検索機能**: リアルタイム検索
- **✏️ 編集・削除**: ワンクリックで操作
- **📱 レスポンシブ対応**: モバイルデバイスでも快適

### 🚀 REST APIエンドポイント

**ベースURL**: http://localhost:8002

#### メモリエントリ管理
- `POST /memories` - 新しいメモリエントリを作成
- `GET /memories` - メモリエントリを検索・一覧表示
- `GET /memories/{id}` - 特定のメモリエントリを取得
- `PUT /memories/{id}` - メモリエントリを更新
- `DELETE /memories/{id}` - メモリエントリを削除

#### 検索とフィルタリング
- `GET /memories/search?q={query}` - キーワード検索
- `GET /memories/tags/{tag}` - タグによるフィルタリング
- `GET /memories/rules` - ルールタグ付きエントリの取得

#### ヘルスチェック
- `GET /health` - 詳細なヘルスチェック
- `GET /` - サーバー状態確認

## サーバー管理

### 起動とシャットダウン

サーバーは以下の機能を提供します：

- **グレースフルシャットダウン**: Ctrl+C または SIGTERM でサーバーを安全に停止
- **自動設定検証**: 起動時に設定値の妥当性を確認
- **詳細ログ**: 起動プロセスと設定情報の詳細ログ
- **エラーハンドリング**: 起動エラーの詳細な報告

### ログ管理

- ログファイル: `memory_server.log`（デフォルト）
- ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL
- コンソールとファイルの両方に出力
- 第三者ライブラリのログレベル自動調整

## データ構造

### メモリエントリ

```json
{
  "id": 1,
  "content": "メモリの内容",
  "tags": ["プロジェクト", "ルール"],
  "keywords": ["Python", "FastAPI"],
  "summary": "短い要約",
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

### データベーススキーマ

SQLiteデータベース（`memory.db`）に以下のテーブルが作成されます：

- `memory_entries`: メインのメモリエントリテーブル
- 検索パフォーマンス向上のための各種インデックス
- 自動更新タイムスタンプのトリガー

## 開発

### テスト実行

プロジェクトには包括的なテストスイートが含まれています：

```bash
# 全テストを実行（推奨）
python -m pytest

# 個別テストの実行
python test_server_startup.py          # 基本的なサーバー起動テスト
python test_full_server_startup.py     # 完全なサーバー起動テスト
python test_memory_service.py          # データアクセス層テスト
python test_mcp_tools.py               # MCPツール機能テスト
python test_mcp_integration.py         # MCP統合テスト
python test_api.py                     # REST APIテスト

# カバレッジレポート付きテスト（pytest-covがインストールされている場合）
python -m pytest --cov=main --cov-report=html
```

### 依存関係の詳細

requirements.txtに含まれるパッケージ：

```
fastapi>=0.104.0        # 高速なWeb APIフレームワーク
uvicorn>=0.24.0         # ASGIサーバー
fastmcp>=0.1.0          # MCPプロトコル実装
pydantic>=2.0.0         # データバリデーション
pytest>=7.0.0           # テストフレームワーク
jinja2>=3.0.0           # WebUIテンプレートエンジン
python-multipart>=0.0.6 # マルチパートフォーム処理
httpx>=0.25.0           # 非同期HTTPクライアント
```

これらは全て軽量で、外部サービスへの依存がありません。

### プロジェクト構造

```
memory-server-mcp/
├── 📁 配布用ファイル
│   ├── dist/MemoryServerMCP.exe          # EXE配布版（42MB）
│   └── MemoryServerMCP.spec              # PyInstallerビルド設定
├── 📁 コアサーバーファイル
│   ├── main.py                           # MCPサーバー（ポート8000）
│   ├── webui_server.py                   # WebUIサーバー（ポート8001）
│   ├── api_server.py                     # APIサーバー（ポート8002）
│   └── requirements.txt                  # Python依存関係
├── 📁 WebUI関連
│   ├── templates/                        # HTMLテンプレート
│   │   ├── base.html                     # ベーステンプレート
│   │   ├── index.html                    # メイン画面
│   │   ├── create.html                   # 作成フォーム
│   │   ├── edit.html                     # 編集フォーム
│   │   └── error.html                    # エラー画面
│   └── static/                           # 静的ファイル
│       ├── css/style.css                 # スタイルシート
│       └── js/app.js                     # JavaScript
├── 📁 ビルド関連
│   ├── build_windows_exe.py              # EXE版ビルドスクリプト
│   └── pyinstaller_hooks/                # PyInstallerフック
├── 📁 テストファイル群
│   ├── test_api.py                       # REST APIテスト
│   ├── test_memory_service.py            # データアクセス層テスト
│   ├── test_mcp_tools.py                 # MCPツールテスト
│   ├── test_mcp_integration.py           # MCP統合テスト
│   ├── test_server_startup.py            # サーバー起動テスト
│   └── test_full_server_startup.py       # 完全起動テスト
├── 📁 データと設定
│   ├── memory.db                         # SQLiteデータベース
│   ├── memory_server.log                 # ログファイル
│   ├── mcp_config_cursor.json            # Cursor設定例
│   └── 要件.md                          # プロジェクト要件
└── 📁 その他
    ├── README.md                         # このドキュメント
    └── .git/                            # Gitリポジトリ
```

### 重要なファイル

#### 実行ファイル
- **dist/MemoryServerMCP.exe**: EXE版配布ファイル（推奨）
- **main.py**: MCPサーバー（ポート8000）
- **webui_server.py**: WebUIサーバー（ポート8001）
- **api_server.py**: APIサーバー（ポート8002）

#### データとログ
- **memory.db**: SQLiteデータベース（ポータブル、バックアップ可能）
- **memory_server.log**: 詳細なログ情報（トラブルシューティング用）

#### 設定と依存関係
- **requirements.txt**: Python依存関係定義
- **mcp_config_cursor.json**: Cursor設定例

## トラブルシューティング

### よくある問題と解決方法

#### 1. サーバー起動エラー

**問題**: `Address already in use` エラー
```bash
# 解決方法: 各ポートを変更
export MEMORY_SERVER_PORT=8100    # MCPサーバー
export MEMORY_WEBUI_PORT=8101     # WebUIサーバー  
export MEMORY_API_PORT=8102       # APIサーバー
python main.py
```

**問題**: `Permission denied` でデータベースファイルにアクセスできない
```bash
# 解決方法: ファイル権限を確認・修正
chmod 644 memory.db
# または、別の場所にデータベースを作成
export MEMORY_DB_PATH=/tmp/memory.db
```

#### 2. MCP接続エラー

**問題**: Cursor IDEでMCPサーバーに接続できない
- EXE版使用時: EXEファイルのパスが正しいか確認
- Python版使用時: 仮想環境が有効化されているか確認
- 各サーバーが実際に起動しているか確認：
  - MCP: `curl http://localhost:8000/health`
  - WebUI: `curl http://localhost:8001`
  - API: `curl http://localhost:8002/health`
- 複数Cursorインスタンス使用時は1つずつ接続を確認

**問題**: MCPツールが表示されない
- `autoApprove` リストにツール名が含まれているか確認
- Cursor IDEでMCPサーバーを再起動（MCP Server Viewから）

#### 3. パフォーマンス問題

**問題**: 検索が遅い
```bash
# 解決方法: 検索結果数を制限
export MEMORY_MAX_SEARCH_RESULTS=50
```

**問題**: メモリ使用量が多い
- データベースファイルのサイズを確認
- 不要なメモリエントリを削除
- ログレベルを WARNING に変更

#### 4. データ関連の問題

**問題**: データが保存されない
- データベースファイルの書き込み権限を確認
- ディスク容量を確認
- ログファイルでエラーメッセージを確認

**問題**: 文字化けが発生
- UTF-8エンコーディングが使用されているか確認
- 環境変数 `PYTHONIOENCODING=utf-8` を設定

### ログの確認方法

詳細なエラー情報は以下の方法で確認できます：

```bash
# リアルタイムでログを監視
tail -f memory_server.log

# エラーレベルのログのみ表示
grep "ERROR\|CRITICAL" memory_server.log

# 最新の100行を表示
tail -n 100 memory_server.log
```

### デバッグモード

より詳細な情報が必要な場合：

```bash
# デバッグレベルでログを出力
export MEMORY_LOG_LEVEL=DEBUG
python main.py
```

### サポートとフィードバック

問題が解決しない場合：
1. `memory_server.log` の関連部分を確認
2. 環境情報（OS、Pythonバージョン）を記録
3. 再現手順を明確にする
4. GitHubのIssueで報告

## 💡 使用例

### 🌐 Web UI を使用した基本操作

1. **ブラウザで http://localhost:8001 にアクセス**
2. **「新規作成」ボタンクリック**
3. **メモリエントリを入力**：
   - 内容: "プロジェクトではPEP8を厳密に守る"
   - タグ: "ルール", "コーディング規約"
   - キーワード: "PEP8", "Python"
   - 要約: "Pythonコーディング規約の方針"
4. **保存後、一覧画面で確認・検索・編集が可能**

### 🤖 Cursor/Claude での MCP 活用フロー

1. **プロジェクトルールの保存**:
```bash
# CursorでLLMに以下のように指示
"このプロジェクトでは、Pythonのコーディング規約としてPEP8を厳密に守り、型ヒントを必須とする、というルールをメモリに保存してください"
```

2. **技術的な決定事項の記録**:
```bash
"FastAPIとSQLiteを使用する理由は軽量性とポータビリティを重視するため、という決定をメモリに保存してください"
```

3. **後の会話での自動参照**:
```bash
# LLMは自動的に保存されたルールを参照して回答
"新しいAPIエンドポイントを作成したいのですが..."
# → LLMは保存されたコーディング規約に基づいて提案
```

### REST API使用例

```bash
# メモリエントリを作成（API Server使用）
curl -X POST "http://localhost:8002/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "プロジェクトではPEP8を厳密に守る",
    "tags": ["ルール", "コーディング規約"],
    "keywords": ["PEP8", "Python", "コーディング"],
    "summary": "Pythonコーディング規約の方針"
  }'

# キーワードで検索
curl "http://localhost:8002/memories/search?q=PEP8"

# タグで検索
curl "http://localhost:8002/memories/tags/ルール"

# WebUI経由でのAPI呼び出し
curl "http://localhost:8001/api/memories"
```

## データのバックアップと移行

### バックアップ

```bash
# データベースファイルをコピー
cp memory.db memory_backup_$(date +%Y%m%d).db

# 設定ファイルも含めてバックアップ
tar -czf memory_server_backup.tar.gz memory.db memory_server.log .kiro/
```

### 他のマシンへの移行

```bash
# 1. プロジェクトファイルをコピー
scp -r memory-server-mcp/ user@newmachine:/path/to/destination/

# 2. 新しいマシンで依存関係をインストール
cd /path/to/destination/memory-server-mcp/
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. サーバーを起動
python main.py
```

## パフォーマンスと制限事項

### 推奨使用量
- **メモリエントリ数**: 10,000件まで（快適な検索速度を維持）
- **1エントリあたりのサイズ**: 10KB以下（大きなコードブロックは要約を活用）
- **同時接続数**: 10接続まで（個人使用想定）

### システム要件
- **RAM**: 最小256MB、推奨512MB
- **ディスク容量**: 最小100MB、推奨1GB
- **CPU**: 任意（軽量設計のため低スペックでも動作）

## セキュリティ考慮事項

- **ローカル実行**: 外部ネットワーク通信なし
- **データ暗号化**: SQLiteファイルは平文（必要に応じて暗号化可能）
- **アクセス制御**: localhostのみからのアクセス
- **ログ管理**: 機密情報のログ出力を避ける設計

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグ報告や機能要求は、GitHubのIssueでお知らせください。プルリクエストも歓迎します。

## 📋 更新履歴

- **v2.0.0** (2025-01-01): 3サーバーアーキテクチャ完成版
  - 🏗️ 3サーバー分離アーキテクチャ実装
  - 🌐 WebUI統合（ポート8001）
  - 🚀 独立APIサーバー（ポート8002）
  - 📦 EXE版配布パッケージ（42MB）
  - 🔧 複数Cursor接続対応
  - 🎨 レスポンシブWebUI
  - 📊 包括的テストスイート拡張

- **v1.0.0**: 初回リリース
  - MCP統合機能
  - REST API
  - SQLiteデータベース
  - 基本テストスイート