#!/usr/bin/env python3
"""
Memory Server MCP - Build with Custom Hooks
カスタムフックを使用してアプリをビルド
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_with_hooks():
    """カスタムフックを使用してアプリをビルド"""
    
    print("=== Memory Server MCP - Build with Custom Hooks ===")
    
    # フックディレクトリのパス
    hooks_dir = Path("pyinstaller_hooks").absolute()
    
    app_name = "MemoryServerMCP"
    
    # コンソール版をビルド
    print("\n--- コンソール版をビルド中 ---")
    console_args = [
        "pyinstaller",
        "--name", f"{app_name}-Console",
        "--onefile",
        "--console",
        "--noconfirm",
        "--clean",
        "--additional-hooks-dir", str(hooks_dir),
        "--copy-metadata", "fastmcp",
        "--copy-metadata", "mcp",
        "--hidden-import", "importlib.metadata",
        "--hidden-import", "pkg_resources",
        "main.py"
    ]
    
    try:
        result = subprocess.run(console_args, check=True, capture_output=True, text=True)
        print("✓ コンソール版のビルドが完了しました")
        
        console_path = Path("dist") / f"{app_name}-Console"
        if console_path.exists():
            print(f"✓ 実行ファイル: {console_path}")
            os.chmod(console_path, 0o755)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ コンソール版ビルドエラー: {e}")
        print(f"stderr: {e.stderr}")
        return False
    
    # GUI版もビルド
    print("\n--- GUI版をビルド中 ---")
    gui_args = [
        "pyinstaller",
        "--name", app_name,
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--additional-hooks-dir", str(hooks_dir),
        "--copy-metadata", "fastmcp",
        "--copy-metadata", "mcp",
        "--hidden-import", "importlib.metadata",
        "--hidden-import", "pkg_resources",
        "main.py"
    ]
    
    try:
        result = subprocess.run(gui_args, check=True, capture_output=True, text=True)
        print("✓ GUI版のビルドが完了しました")
        
        gui_path = Path("dist") / app_name
        if gui_path.exists():
            print(f"✓ 実行ファイル: {gui_path}")
            os.chmod(gui_path, 0o755)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ GUI版ビルドエラー: {e}")
        print(f"stderr: {e.stderr}")
        return False
    
    # .appバンドルを作成
    create_app_bundle(app_name)
    
    print("\n=== ビルド完了 ===")
    print("作成されたファイル:")
    print(f"  dist/{app_name}-Console (コンソール版 - 推奨)")
    print(f"  dist/{app_name} (GUI版)")
    print(f"  dist/{app_name}.app (macOSアプリバンドル)")
    
    return True

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
        source_file = Path("dist") / app_name
        if source_file.exists():
            shutil.copy2(source_file, macos_path / app_name)
            os.chmod(macos_path / app_name, 0o755)
        
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
    build_with_hooks()