#!/usr/bin/env python3
"""
Memory Server MCP - Automator App Creator
macOS Automator用のアプリケーション作成スクリプト
"""

import os
import subprocess
from pathlib import Path

def create_automator_app():
    """Automator用のスクリプトとアプリを作成"""
    
    print("=== Memory Server MCP - Automator App Creator ===")
    
    # 起動スクリプトを作成
    launch_script = f"""#!/bin/bash

# Memory Server MCP 起動スクリプト
cd "{os.getcwd()}"

# 仮想環境があればアクティベート
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Pythonでサーバーを起動
python3 main.py &

# サーバーが起動するまで少し待つ
sleep 3

# ブラウザでサーバーを開く
open http://localhost:8000

# ターミナルを開いてログを表示
osascript -e 'tell application "Terminal" to do script "cd \\"{os.getcwd()}\\" && echo \\"Memory Server MCP が起動しました\\" && echo \\"サーバーを停止するには Ctrl+C を押してください\\""'
"""
    
    script_path = Path("launch_memory_server.sh")
    with open(script_path, "w") as f:
        f.write(launch_script)
    
    # 実行権限を付与
    os.chmod(script_path, 0o755)
    
    print(f"✓ 起動スクリプトを作成しました: {script_path}")
    
    # Automator用の手順を表示
    print("\n=== Automator アプリの作成手順 ===")
    print("1. Automator.app を開く")
    print("2. 'アプリケーション' を選択")
    print("3. 左側から 'シェルスクリプトを実行' をドラッグ")
    print("4. 以下のスクリプトをコピー&ペースト:")
    print(f"   {script_path.absolute()}")
    print("5. ファイル > 保存 で 'Memory Server MCP.app' として保存")
    print("6. 保存したアプリをダブルクリックで起動")
    
    # AppleScript版も作成
    applescript_content = f'''
on run
    set currentPath to "{os.getcwd()}"
    
    tell application "Terminal"
        activate
        do script "cd \\"" & currentPath & "\\" && python3 main.py"
    end tell
    
    delay 3
    
    tell application "Safari"
        activate
        open location "http://localhost:8000"
    end tell
    
end run
'''
    
    applescript_path = Path("Memory Server MCP.scpt")
    with open(applescript_path, "w") as f:
        f.write(applescript_content)
    
    print(f"\n✓ AppleScriptも作成しました: {applescript_path}")
    print("このファイルをScript Editorで開いて、アプリケーションとして保存できます")

if __name__ == "__main__":
    create_automator_app()