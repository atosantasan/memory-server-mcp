# 技術スタック

## 核となる技術
- **言語**: Python（クロスプラットフォーム、優秀なSQLite統合）
- **Webフレームワーク**: FastAPI（軽量、高速、シンプルなAPI定義）
- **ASGIサーバー**: Uvicorn（FastAPI用軽量サーバー）
- **MCP統合**: FastMCP（MCPプロトコル実装の簡素化）
- **データベース**: SQLite3（Python標準ライブラリ、単一ファイル、軽量）

## 主要ライブラリ
- `fastapi` - APIエンドポイント用Webフレームワーク
- `uvicorn` - FastAPI実行用ASGIサーバー
- `fastmcp` - MCPプロトコル実装
- `sqlite3` - データベース操作（Python標準ライブラリ）

## アーキテクチャ原則
- **単一プロセス**: 外部依存なしでスタンドアロンサーバーとして動作
- **MCPプロトコル**: LLM統合用ツールとしてメモリ操作を公開
- **RESTful API**: メモリエントリのCRUD操作用HTTPエンドポイント
- **ファイルベースストレージ**: ポータブルなデータ永続化用SQLiteデータベース

## よく使うコマンド

### 開発環境セットアップ
```bash
# 仮想環境作成
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 依存関係インストール
pip install fastapi uvicorn fastmcp
```

### サーバー起動
```bash
# メモリサーバー開始
python main.py

# または直接uvicornを使用
uvicorn main:app --host localhost --port 8000
```

### データベース操作
- データベースファイル: `memory.db`（SQLite）
- 初回実行時に自動スキーマ作成
- 手動データベースセットアップ不要

## 開発ガイドライン
- パフォーマンスより安定性を優先
- 依存関係を最小限に保つ
- クロスプラットフォーム互換性を確保
- 可能な限りPython標準ライブラリを使用
- MCPツール用の適切なエラーハンドリングを実装