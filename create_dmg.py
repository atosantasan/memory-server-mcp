#!/usr/bin/env python3
"""
Memory Server MCP - DMG Creator
配布用のDMGファイルを作成
"""

import os
import subprocess
import shutil
from pathlib import Path

def create_dmg():
    """DMGファイルを作成"""
    
    print("=== Memory Server MCP - DMG Creator ===")
    
    # 必要なファイルの確認
    app_path = Path("dist/MemoryServerMCP.app")
    if not app_path.exists():
        print("❌ MemoryServerMCP.app が見つかりません")
        print("先に ./setup_app.sh を実行してください")
        return False
    
    # DMG作成用の一時ディレクトリを作成
    dmg_temp_dir = Path("dmg_temp")
    if dmg_temp_dir.exists():
        shutil.rmtree(dmg_temp_dir)
    dmg_temp_dir.mkdir()
    
    try:
        # アプリをコピー
        print("アプリケーションをコピーしています...")
        shutil.copytree(app_path, dmg_temp_dir / "Memory Server MCP.app")
        
        # README.txtを作成
        readme_content = """Memory Server MCP - 個人用メモリサーバー

=== インストール方法 ===
1. "Memory Server MCP.app" をアプリケーションフォルダにドラッグ&ドロップ
2. アプリケーションフォルダから "Memory Server MCP" をダブルクリックで起動

=== 使用方法 ===
1. アプリを起動すると自動でサーバーが開始されます
2. ブラウザで http://localhost:8000 にアクセス
3. MCPプロトコルでCursor/Claudeから利用可能

=== 機能 ===
- メモリエントリの作成・編集・削除
- タグとキーワードによる分類
- 高速検索機能
- REST API提供
- MCP (Model Context Protocol) 対応

=== システム要件 ===
- macOS 10.15 (Catalina) 以降
- 空きディスク容量: 100MB以上

=== サポート ===
問題が発生した場合は、ターミナルから以下のコマンドでログを確認してください：
tail -f ~/Library/Logs/MemoryServerMCP/memory_server.log

=== バージョン ===
Version 1.0.0
"""
        
        with open(dmg_temp_dir / "README.txt", "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        # アプリケーションフォルダへのシンボリックリンクを作成
        applications_link = dmg_temp_dir / "Applications"
        os.symlink("/Applications", applications_link)
        
        print("DMGファイルを作成しています...")
        
        # hdiutilを使ってDMGを作成
        dmg_name = "Memory-Server-MCP-v1.0.0.dmg"
        
        # 既存のDMGファイルを削除
        if Path(dmg_name).exists():
            os.remove(dmg_name)
        
        # DMG作成コマンド
        create_dmg_cmd = [
            "hdiutil", "create",
            "-volname", "Memory Server MCP",
            "-srcfolder", str(dmg_temp_dir),
            "-ov",
            "-format", "UDZO",
            "-imagekey", "zlib-level=9",
            dmg_name
        ]
        
        result = subprocess.run(create_dmg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ DMGファイルが作成されました: {dmg_name}")
            
            # ファイルサイズを表示
            dmg_size = Path(dmg_name).stat().st_size / (1024 * 1024)
            print(f"  ファイルサイズ: {dmg_size:.1f} MB")
            
            print("\n=== 配布方法 ===")
            print(f"1. {dmg_name} を配布")
            print("2. ユーザーはDMGをマウントしてアプリをApplicationsフォルダにドラッグ")
            print("3. アプリケーションフォルダから起動")
            
            return True
        else:
            print(f"❌ DMG作成エラー: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False
    finally:
        # 一時ディレクトリを削除
        if dmg_temp_dir.exists():
            shutil.rmtree(dmg_temp_dir)

def create_zip_distribution():
    """ZIP形式の配布パッケージも作成"""
    print("\n=== ZIP配布パッケージの作成 ===")
    
    app_path = Path("dist/MemoryServerMCP.app")
    if not app_path.exists():
        print("❌ MemoryServerMCP.app が見つかりません")
        return False
    
    try:
        zip_name = "Memory-Server-MCP-v1.0.0.zip"
        
        # 既存のZIPファイルを削除
        if Path(zip_name).exists():
            os.remove(zip_name)
        
        # ZIPファイルを作成
        shutil.make_archive(
            "Memory-Server-MCP-v1.0.0",
            "zip",
            "dist",
            "MemoryServerMCP.app"
        )
        
        zip_size = Path(zip_name).stat().st_size / (1024 * 1024)
        print(f"✓ ZIPファイルが作成されました: {zip_name}")
        print(f"  ファイルサイズ: {zip_size:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ ZIP作成エラー: {e}")
        return False

if __name__ == "__main__":
    success = create_dmg()
    if success:
        create_zip_distribution()
        print("\n=== 配布パッケージの作成完了 ===")
        print("DMGファイルとZIPファイルの両方が作成されました")
    else:
        print("❌ 配布パッケージの作成に失敗しました")