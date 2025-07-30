#!/usr/bin/env python3
"""
Memory Server MCP - macOS App Builder
PyInstallerを使ってスタンドアロンアプリケーションを作成
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_macos_app():
    """macOS用アプリケーションをビルド"""
    
    print("=== Memory Server MCP - macOS App Builder ===")
    
    # 必要なパッケージの確認
    try:
        import PyInstaller
        print("✓ PyInstaller が見つかりました")
    except ImportError:
        print("PyInstaller をインストールしています...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✓ PyInstaller をインストールしました")
    
    # ビルド設定
    app_name = "MemoryServerMCP"
    main_script = "main.py"
    
    # まずコンソール版をビルド（デバッグ用）
    build_console_version(app_name, main_script)
    
    # 次にGUI版をビルド
    build_gui_version(app_name, main_script)

def build_console_version(app_name, main_script):
    """コンソール版をビルド（デバッグしやすい）"""
    print("\n--- コンソール版をビルド中 ---")
    
    console_args = [
        "pyinstaller",
        "--name", f"{app_name}-Console",
        "--onedir",
        "--console",  # コンソールウィンドウを表示
        "--noconfirm",
        "--clean",
        "--add-data", "requirements.txt:.",
        "--hidden-import", "fastapi",
        "--hidden-import", "uvicorn",
        "--hidden-import", "fastmcp",
        "--hidden-import", "sqlite3",
        "--hidden-import", "pydantic",
        "--hidden-import", "importlib.metadata",
        "--hidden-import", "pkg_resources",
        "--collect-all", "fastmcp",
        "--copy-metadata", "fastmcp",
        "--copy-metadata", "mcp",
        "--copy-metadata", "fastapi",
        "--copy-metadata", "uvicorn",
        "--copy-metadata", "pydantic",
        main_script
    ]
    
    try:
        subprocess.run(console_args, check=True, capture_output=True, text=True)
        print("✓ コンソール版のビルドが完了しました")
    except subprocess.CalledProcessError as e:
        print(f"❌ コンソール版のビルドエラー: {e}")
        print(f"stderr: {e.stderr}")

def build_gui_version(app_name, main_script):
    """GUI版をビルド"""
    print("\n--- GUI版をビルド中 ---")
    
    # PyInstaller コマンドを構築
    pyinstaller_args = [
        "pyinstaller",
        "--name", app_name,
        "--onedir",  # 一つのディレクトリにまとめる
        "--windowed",  # コンソールウィンドウを表示しない
        "--noconfirm",  # 既存ファイルを上書き
        "--clean",  # キャッシュをクリア
        "--add-data", "requirements.txt:.",  # requirements.txtを含める
        "--hidden-import", "fastapi",
        "--hidden-import", "uvicorn",
        "--hidden-import", "fastmcp",
        "--hidden-import", "sqlite3",
        "--hidden-import", "pydantic",
        "--hidden-import", "importlib.metadata",
        "--hidden-import", "pkg_resources",
        "--collect-all", "fastmcp",  # fastmcpの全てのファイルを含める
        "--copy-metadata", "fastmcp", # fastmcpのメタデータを含める
        "--copy-metadata", "mcp",     # mcpのメタデータを含める
        "--copy-metadata", "fastapi",
        "--copy-metadata", "uvicorn",
        "--copy-metadata", "pydantic",
        main_script
    ]
    
    print(f"GUI版アプリケーション '{app_name}' をビルドしています...")
    print(f"コマンド: {' '.join(pyinstaller_args)}")
    
    try:
        # PyInstaller実行
        result = subprocess.run(pyinstaller_args, check=True, capture_output=True, text=True)
        print("✓ GUI版のビルドが完了しました")
        
        # 結果の確認
        app_path = Path("dist") / app_name
        console_path = Path("dist") / f"{app_name}-Console"
        
        if app_path.exists():
            print(f"✓ GUI版アプリケーションが作成されました: {app_path}")
            
            # .appバンドルを作成（オプション）
            create_app_bundle(app_name)
            
        if console_path.exists():
            print(f"✓ コンソール版アプリケーションが作成されました: {console_path}")
            
        print("\n=== 使用方法 ===")
        print("【推奨】コンソール版（エラーが見える）:")
        print(f"  dist/{app_name}-Console/{app_name}-Console をダブルクリック")
        print("\nGUI版（バックグラウンド実行）:")
        print(f"  dist/{app_name}/{app_name} をダブルクリック")
        print(f"  または dist/{app_name}.app をダブルクリック")
        print("\n起動後: ブラウザで http://localhost:8000 にアクセス")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ GUI版ビルドエラー: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")

def create_app_bundle(app_name):
    """macOS用の.appバンドルを作成"""
    try:
        app_bundle_path = Path("dist") / f"{app_name}.app"
        contents_path = app_bundle_path / "Contents"
        macos_path = contents_path / "MacOS"
        resources_path = contents_path / "Resources"
        
        # ディレクトリ構造を作成
        macos_path.mkdir(parents=True, exist_ok=True)
        resources_path.mkdir(parents=True, exist_ok=True)
        
        # 実行ファイルをコピー
        source_app = Path("dist") / app_name
        if source_app.exists():
            # 実行ファイルをMacOSフォルダにコピー
            for item in source_app.iterdir():
                if item.is_file() and item.name == app_name:
                    shutil.copy2(item, macos_path / app_name)
                elif item.is_dir():
                    shutil.copytree(item, macos_path / item.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, macos_path)
        
        # Info.plistを作成
        info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>{app_name}</string>
    <key>CFBundleIdentifier</key>
    <string>com.memoryserver.mcp</string>
    <key>CFBundleName</key>
    <string>Memory Server MCP</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>"""
        
        with open(contents_path / "Info.plist", "w") as f:
            f.write(info_plist)
        
        print(f"✓ .appバンドルを作成しました: {app_bundle_path}")
        
    except Exception as e:
        print(f"⚠️  .appバンドルの作成に失敗: {e}")

if __name__ == "__main__":
    build_macos_app()