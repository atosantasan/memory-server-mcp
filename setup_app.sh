#!/bin/bash

# Memory Server MCP - macOS App Setup Script
# このスクリプトはmacOS用のアプリケーションをセットアップします

echo "=== Memory Server MCP - macOS App Setup ==="

# Python環境の確認
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 が見つかりません。Pythonをインストールしてください。"
    exit 1
fi

echo "✓ Python3 が見つかりました: $(python3 --version)"

# 仮想環境の作成
if [ ! -d "venv" ]; then
    echo "仮想環境を作成しています..."
    python3 -m venv venv
    echo "✓ 仮想環境を作成しました"
fi

# 仮想環境をアクティベート
source venv/bin/activate
echo "✓ 仮想環境をアクティベートしました"

# 依存関係のインストール
echo "依存関係をインストールしています..."
pip install --upgrade pip

# requirements.txtがある場合はそれを使用、なければ直接インストール
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install fastapi uvicorn fastmcp pydantic
fi

# GUI用の追加パッケージ
pip install pyinstaller

echo "✓ 依存関係のインストールが完了しました"

# アプリケーションのビルド
echo "アプリケーションをビルドしています..."
python3 build_app.py

echo ""
echo "=== セットアップ完了 ==="
echo "以下の方法でアプリケーションを起動できます："
echo ""
echo "方法1: GUIランチャーを使用"
echo "  python3 launcher.py"
echo ""
echo "方法2: ビルドされたアプリを使用"
echo "  dist/MemoryServerMCP/MemoryServerMCP をダブルクリック"
echo ""
echo "方法3: 直接実行"
echo "  python3 main.py"
echo ""
echo "サーバーが起動したら http://localhost:8000 にアクセスしてください"