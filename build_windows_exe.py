#!/usr/bin/env python3
"""
Memory Server MCP - Windows EXE Builder
Windows用の単体実行ファイル(.exe)を作成するためのビルドスクリプト
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import platform

def check_python_requirements():
    """必要なPythonパッケージがインストールされているかチェック"""
    print("=== 必要なパッケージのチェック ===")
    
    required_packages = {
        'PyInstaller': 'pyinstaller',
        'fastapi': 'fastapi>=0.104.0',
        'uvicorn': 'uvicorn>=0.24.0', 
        'fastmcp': 'fastmcp>=0.1.0',
        'pydantic': 'pydantic>=2.0.0'
    }
    
    missing_packages = []
    
    for package_name, pip_name in required_packages.items():
        try:
            __import__(package_name.lower())
            print(f"✓ {package_name} がインストールされています")
        except ImportError:
            print(f"❌ {package_name} がインストールされていません")
            missing_packages.append(pip_name)
    
    if missing_packages:
        print(f"\n以下のパッケージをインストールしています: {', '.join(missing_packages)}")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install"
            ] + missing_packages, check=True)
            print("✓ 必要なパッケージのインストールが完了しました")
        except subprocess.CalledProcessError as e:
            print(f"❌ パッケージのインストールに失敗しました: {e}")
            return False
    
    return True

def clean_build_directory():
    """ビルドディレクトリをクリーンアップ"""
    print("\n=== ビルドディレクトリのクリーンアップ ===")
    
    dirs_to_clean = ["build", "dist", "__pycache__"]
    files_to_clean = ["*.spec"]
    
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"✓ {dir_name} ディレクトリを削除しました")
    
    # .specファイルを削除
    for spec_file in Path(".").glob("*.spec"):
        spec_file.unlink()
        print(f"✓ {spec_file} を削除しました")

def build_windows_exe():
    """Windows用EXEファイルをビルド"""
    print("\n=== Windows EXE ビルド開始 ===")
    
    # アプリケーション名
    app_name = "MemoryServerMCP"
    main_script = "main.py"
    
    # メインスクリプトが存在するかチェック
    if not Path(main_script).exists():
        print(f"❌ {main_script} が見つかりません")
        return False
    
    # フックディレクトリのパス
    hooks_dir = Path("pyinstaller_hooks").absolute()
    
    # PyInstaller コマンドライン引数を構築
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--name", app_name,
        "--onefile",  # 単一実行ファイル
        "--console",  # コンソールウィンドウを表示（エラーログ確認用）
        "--noconfirm",  # 既存ファイルを上書き
        "--clean",  # キャッシュをクリア
        "--noupx",  # UPX圧縮を無効化（互換性向上）
        
        # カスタムフックディレクトリ
        "--additional-hooks-dir", str(hooks_dir),
        
        # メタデータのコピー（重要: インポートエラー防止）
        "--copy-metadata", "fastmcp",
        "--copy-metadata", "mcp",
        "--copy-metadata", "fastapi", 
        "--copy-metadata", "uvicorn",
        "--copy-metadata", "pydantic",
        "--copy-metadata", "pydantic-core",
        "--copy-metadata", "typing-extensions",
        "--copy-metadata", "starlette",
        
        # 隠された依存関係を明示的にインポート
        "--hidden-import", "fastapi",
        "--hidden-import", "fastapi.applications",
        "--hidden-import", "fastapi.routing",
        "--hidden-import", "fastapi.middleware",
        "--hidden-import", "fastapi.middleware.cors",
        "--hidden-import", "fastapi.exceptions",
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.main", 
        "--hidden-import", "uvicorn.config",
        "--hidden-import", "uvicorn.server",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "fastmcp",
        "--hidden-import", "fastmcp.server",
        "--hidden-import", "fastmcp.server.server",
        "--hidden-import", "fastmcp.server.context",
        "--hidden-import", "fastmcp.client",
        "--hidden-import", "fastmcp.utilities.logging",
        "--hidden-import", "sqlite3",
        "--hidden-import", "pydantic",
        "--hidden-import", "pydantic.fields",
        "--hidden-import", "pydantic.main",
        "--hidden-import", "pydantic.validators",
        "--hidden-import", "pydantic._internal",
        "--hidden-import", "importlib.metadata",
        "--hidden-import", "pkg_resources",
        "--hidden-import", "asyncio",
        "--hidden-import", "asyncio.events",
        "--hidden-import", "asyncio.protocols",
        "--hidden-import", "asyncio.transports",
        "--hidden-import", "asyncio.selector_events",
        "--hidden-import", "asyncio.proactor_events",
        "--hidden-import", "json",
        "--hidden-import", "logging",
        "--hidden-import", "logging.handlers",
        "--hidden-import", "datetime",
        "--hidden-import", "typing",
        "--hidden-import", "typing_extensions",
        "--hidden-import", "dataclasses",
        
        # Windows固有のインポート
        "--hidden-import", "multiprocessing",
        "--hidden-import", "multiprocessing.reduction",
        "--hidden-import", "multiprocessing.spawn",
        
        # 必要なファイルを含める
        "--add-data", "requirements.txt;.",
        
        # 全体のファイル収集（必要に応じて）
        "--collect-all", "fastmcp",
        "--collect-all", "pydantic",
        
        # メインスクリプト
        main_script
    ]
    
    print(f"実行コマンド: {' '.join(pyinstaller_args[:10])}... (省略)")
    print("ビルドを開始します...")
    
    try:
        # PyInstaller実行
        result = subprocess.run(
            pyinstaller_args, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=Path.cwd()
        )
        
        print("✓ PyInstallerのビルドが完了しました")
        
        # 結果の確認
        exe_path = Path("dist") / f"{app_name}.exe"
        
        if exe_path.exists():
            file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
            print(f"✓ 実行ファイルが作成されました: {exe_path}")
            print(f"  ファイルサイズ: {file_size:.1f} MB")
            
            # 実行テスト
            print("\n実行ファイルのクイックテスト...")
            test_result = subprocess.run(
                [str(exe_path), "--help"], 
                capture_output=True, 
                text=True,
                timeout=10  # 10秒でタイムアウト
            )
            
            if test_result.returncode == 0:
                print("✓ 実行ファイルは正常に動作します")
            else:
                print(f"⚠️  実行ファイルのテストで警告: {test_result.stderr}")
            
            return True
        else:
            print("❌ 実行ファイルが作成されませんでした")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ ビルドエラー: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️  実行テストがタイムアウトしましたが、ビルドは成功しています")
        return True
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

def create_batch_launcher():
    """実行用のバッチファイルを作成"""
    print("\n=== 起動用バッチファイルの作成 ===")
    
    batch_content = '''@echo off
echo Memory Server MCP を起動しています...
echo.
echo サーバーが起動したら、ブラウザで http://localhost:8000 にアクセスしてください
echo 終了するには Ctrl+C を押してください
echo.

cd /d "%~dp0"
MemoryServerMCP.exe

pause
'''
    
    batch_path = Path("dist") / "start_server.bat"
    
    try:
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        
        print(f"✓ バッチファイルを作成しました: {batch_path}")
        return True
    except Exception as e:
        print(f"❌ バッチファイルの作成に失敗: {e}")
        return False

def create_readme():
    """README.txtファイルを作成"""
    print("\n=== 使用方法説明ファイルの作成 ===")
    
    readme_content = '''Memory Server MCP - 使用方法

【起動方法】
1. start_server.bat をダブルクリック
   または
2. MemoryServerMCP.exe を直接実行

【アクセス方法】
- ブラウザで http://localhost:8000 にアクセス
- Health Check: http://localhost:8000/health

【MCP Protocol】
- stdio経由でMCPプロトコルを使用
- Cursor/Claude等のAIツールから利用可能

【終了方法】
- Ctrl+C を押すか、コンソールウィンドウを閉じてください

【ファイル構成】
- MemoryServerMCP.exe: メインアプリケーション
- start_server.bat: 起動用バッチファイル
- memory.db: データベースファイル（自動生成）
- memory_server.log: ログファイル

【トラブルシューティング】
1. ポート8000が使用中の場合:
   環境変数 MEMORY_SERVER_PORT で変更可能
   
2. データベースエラーの場合:
   memory.db ファイルを削除して再実行

3. 詳細なログを確認:
   memory_server.log ファイルを参照

【環境変数】
- MEMORY_SERVER_HOST: サーバーのホスト（デフォルト: localhost）
- MEMORY_SERVER_PORT: サーバーのポート（デフォルト: 8000）
- MEMORY_LOG_LEVEL: ログレベル（デフォルト: INFO）
- MEMORY_DB_PATH: データベースファイルのパス（デフォルト: memory.db）

作成日: {datetime}
'''
    
    from datetime import datetime
    readme_content = readme_content.format(datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    readme_path = Path("dist") / "README.txt"
    
    try:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"✓ 使用方法説明ファイルを作成しました: {readme_path}")
        return True
    except Exception as e:
        print(f"❌ 説明ファイルの作成に失敗: {e}")
        return False

def main():
    """メイン処理"""
    print("=== Memory Server MCP - Windows EXE Builder ===")
    print(f"Python Version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Architecture: {platform.architecture()[0]}")
    
    # Windowsプラットフォームの確認
    if not sys.platform.startswith('win'):
        print("⚠️  このスクリプトはWindows用です")
        print("他のプラットフォーム用のビルドスクリプトを使用してください")
        return 1
    
    # 1. 必要なパッケージのチェック
    if not check_python_requirements():
        return 1
    
    # 2. ビルドディレクトリのクリーンアップ  
    clean_build_directory()
    
    # 3. EXEファイルのビルド
    if not build_windows_exe():
        return 1
    
    # 4. 補助ファイルの作成
    create_batch_launcher()
    create_readme()
    
    # 5. 成功メッセージ
    print("\n" + "="*50)
    print("✓ ビルドが正常に完了しました！")
    print("="*50)
    print("\n作成されたファイル:")
    
    dist_path = Path("dist")
    if dist_path.exists():
        for file_path in dist_path.iterdir():
            if file_path.is_file():
                size = file_path.stat().st_size
                if size > 1024*1024:
                    size_str = f"{size/(1024*1024):.1f} MB"
                elif size > 1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size} bytes"
                print(f"  {file_path.name} ({size_str})")
    
    print("\n使用方法:")
    print("  1. dist\\start_server.bat をダブルクリック")
    print("  2. ブラウザで http://localhost:8000 にアクセス")
    print("  3. 詳細は dist\\README.txt を参照")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())