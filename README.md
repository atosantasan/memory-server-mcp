# Memory Server MCP

個人用メモリサーバー - Cursor/Claude統合用のMCP（Model Context Protocol）準拠サーバー

## 概要

このプロジェクトは、長時間の会話におけるコンテキスト喪失問題を解決するため、MCP（Model Context Protocol）を通じてCursor/Claudeと統合する個人用メモリサーバーです。LLMに長期記憶機能を提供し、保存された情報を能動的に参照・活用することで、より一貫性があり効率的な開発支援を実現します。

## 主な機能

- **メモリエントリ管理**: テキスト情報をタグ、キーワード、要約と共に保存
- **検索機能**: キーワードやタグによる柔軟な検索
- **MCP統合**: LLMが直接アクセス可能なツール群
- **REST API**: HTTP経由でのメモリ操作
- **軽量設計**: SQLiteベースの単一ファイルデータベース
- **ローカル実行**: 外部依存なしの完全ローカル動作
- **ポータブル**: 単一ファイルデータベースによる簡単な移行
- **安定性重視**: 速度よりも信頼性を優先した設計

## インストール

### 必要な環境

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

#### 4. 初回起動とテスト

```bash
# サーバーを起動（初回実行時にデータベースが自動作成されます）
python main.py
```

正常に起動すると、以下のようなメッセージが表示されます：
```
INFO - Memory Server starting...
INFO - Database initialized at: memory.db
INFO - MCP server started
INFO - FastAPI server started on http://localhost:8000
INFO - Memory Server is ready!
```

#### 5. 動作確認

別のターミナルで以下のコマンドを実行して、サーバーが正常に動作していることを確認：

```bash
# ヘルスチェック
curl http://localhost:8000/health

# または、ブラウザで http://localhost:8000 にアクセス
```

## 使用方法

### サーバー起動

#### 通常起動（MCP + REST API）
```bash
python main.py
```

サーバーが正常に起動すると、以下の機能が利用可能になります：
- **MCPサーバー**: LLMからのツール呼び出しを受け付け
- **REST API**: HTTP経由でのメモリ操作（ポート8000）
- **自動データベース初期化**: 初回起動時にSQLiteデータベースを作成

#### REST APIのみ起動（テスト・開発用）
```bash
python main.py --api-only
```

#### 設定確認モード
```bash
python main.py --check-config
```

### Cursor/ClaudeでのMCP設定

このメモリサーバーをCursor IDEで使用するには、MCP設定ファイルを作成する必要があります：

#### 1. MCP設定ファイルの作成

**ワークスペースレベル設定** (`.kiro/settings/mcp.json`):
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
        "list_all_memories"
      ]
    }
  }
}
```

**ユーザーレベル設定** (`~/.kiro/settings/mcp.json`):
```json
{
  "mcpServers": {
    "memory-server": {
      "command": "python",
      "args": ["/absolute/path/to/main.py"],
      "env": {
        "MEMORY_LOG_LEVEL": "WARNING"
      },
      "disabled": false,
      "autoApprove": []
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

### REST APIエンドポイント

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
- `GET /` - サーバー状態確認
- `GET /health` - 詳細なヘルスチェック

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
fastapi>=0.104.0    # 高速なWeb APIフレームワーク
uvicorn>=0.24.0     # ASGIサーバー
fastmcp>=0.1.0      # MCPプロトコル実装
pydantic>=2.0.0     # データバリデーション
pytest>=7.0.0       # テストフレームワーク
```

これらは全て軽量で、外部サービスへの依存がありません。

### プロジェクト構造

```
memory-server-mcp/
├── main.py                           # メインサーバーファイル（全機能を含む）
├── requirements.txt                  # Python依存関係定義
├── README.md                        # プロジェクトドキュメント
├── 要件.md                          # 元の要件定義（日本語）
├── memory.db                        # SQLiteデータベース（実行時自動作成）
├── memory_server.log                # ログファイル（実行時自動作成）
├── .kiro/                           # Kiro IDE設定
│   ├── specs/                       # 機能仕様書
│   │   └── memory-server-mcp/
│   │       ├── requirements.md      # 詳細要件定義
│   │       ├── design.md           # 設計ドキュメント
│   │       └── tasks.md            # 実装タスクリスト
│   └── steering/                    # AI開発ガイダンス
├── test_*.py                        # テストファイル群
│   ├── test_api.py                  # REST APIテスト
│   ├── test_memory_service.py       # データアクセス層テスト
│   ├── test_mcp_tools.py           # MCPツールテスト
│   ├── test_mcp_integration.py     # MCP統合テスト
│   ├── test_server_startup.py      # サーバー起動テスト
│   └── test_full_server_startup.py # 完全起動テスト
├── .venv/                          # Python仮想環境（作成後）
└── __pycache__/                    # Pythonキャッシュ（実行時作成）
```

### 重要なファイル

- **main.py**: 全ての機能を含む単一ファイル（軽量化のため）
- **memory.db**: SQLiteデータベース（ポータブル、バックアップ可能）
- **requirements.txt**: 最小限の依存関係のみ定義
- **memory_server.log**: 詳細なログ情報（トラブルシューティング用）

## トラブルシューティング

### よくある問題と解決方法

#### 1. サーバー起動エラー

**問題**: `Address already in use` エラー
```bash
# 解決方法: 別のポートを使用
export MEMORY_SERVER_PORT=8001
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
- MCP設定ファイルのパスが正しいか確認
- Pythonの仮想環境が有効化されているか確認
- サーバーが実際に起動しているか確認（`curl http://localhost:8000/health`）

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

## 使用例

### 基本的な使用フロー

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
# メモリエントリを作成
curl -X POST "http://localhost:8000/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "プロジェクトではPEP8を厳密に守る",
    "tags": ["ルール", "コーディング規約"],
    "keywords": ["PEP8", "Python", "コーディング"],
    "summary": "Pythonコーディング規約の方針"
  }'

# キーワードで検索
curl "http://localhost:8000/memories/search?q=PEP8"

# タグで検索
curl "http://localhost:8000/memories/tags/ルール"
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

## 更新履歴

- **v1.0.0**: 初回リリース
  - MCP統合機能
  - REST API
  - SQLiteデータベース
  - 包括的なテストスイート