#!/usr/bin/env python3
"""
Memory Server MCP - Kiro IDE Integration
KiroのMCP設定にMemory Serverを追加
"""

import json
import os
from pathlib import Path
import shutil

def add_memory_server_to_kiro():
    """KiroのMCP設定にMemory Serverを追加"""
    
    print("=== Memory Server MCP - Kiro IDE Integration ===")
    
    # 現在のプロジェクトパス
    current_path = Path.cwd().absolute()
    
    # ビルドされたアプリのパス
    app_path = current_path / "dist" / "MemoryServerMCP-Console"
    
    if not app_path.exists():
        print("❌ MemoryServerMCP-Console が見つかりません")
        print("先に build_with_hooks.py を実行してください")
        return False
    
    # Kiro設定ファイルのパス
    kiro_config_path = Path.home() / ".kiro" / "settings" / "mcp.json"
    
    if not kiro_config_path.exists():
        print("❌ Kiro MCP設定ファイルが見つかりません")
        print(f"パス: {kiro_config_path}")
        return False
    
    # 現在の設定を読み込み
    try:
        with open(kiro_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ 設定ファイルの読み込みエラー: {e}")
        return False
    
    # Memory Server MCP設定を追加
    memory_server_config = {
        "command": str(app_path),
        "args": [],
        "env": {
            "MEMORY_SERVER_HOST": "localhost",
            "MEMORY_SERVER_PORT": "8000",
            "MEMORY_LOG_LEVEL": "INFO"
        },
        "disabled": False,
        "autoApprove": [
            "add_note_to_memory",
            "search_memory",
            "list_all_memories",
            "get_project_rules"
        ]
    }
    
    # 既存設定に追加
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    config["mcpServers"]["memory-server"] = memory_server_config
    
    # バックアップを作成
    backup_path = kiro_config_path.with_suffix('.json.backup')
    shutil.copy2(kiro_config_path, backup_path)
    print(f"✓ 設定ファイルのバックアップを作成: {backup_path}")
    
    # 新しい設定を保存
    try:
        with open(kiro_config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("✓ Memory Server MCPをKiro設定に追加しました")
        print(f"  サーバー名: memory-server")
        print(f"  実行ファイル: {app_path}")
        print(f"  自動承認ツール: {len(memory_server_config['autoApprove'])}個")
        
        return True
        
    except Exception as e:
        print(f"❌ 設定ファイルの保存エラー: {e}")
        # バックアップから復元
        shutil.copy2(backup_path, kiro_config_path)
        print("設定ファイルをバックアップから復元しました")
        return False

def create_workspace_config():
    """ワークスペース用のMCP設定も作成"""
    print("\n--- ワークスペース用設定の作成 ---")
    
    workspace_config_dir = Path(".kiro") / "settings"
    workspace_config_dir.mkdir(parents=True, exist_ok=True)
    
    workspace_config_path = workspace_config_dir / "mcp.json"
    
    # 現在のプロジェクトパス
    current_path = Path.cwd().absolute()
    app_path = current_path / "dist" / "MemoryServerMCP-Console"
    
    workspace_config = {
        "mcpServers": {
            "memory-server": {
                "command": str(app_path),
                "args": [],
                "env": {
                    "MEMORY_SERVER_HOST": "localhost",
                    "MEMORY_SERVER_PORT": "8000",
                    "MEMORY_LOG_LEVEL": "INFO",
                    "MEMORY_DB_PATH": str(current_path / "memory.db")
                },
                "disabled": False,
                "autoApprove": [
                    "add_note_to_memory",
                    "search_memory",
                    "list_all_memories",
                    "get_project_rules",
                    "update_memory_entry",
                    "delete_memory_entry"
                ]
            }
        }
    }
    
    try:
        with open(workspace_config_path, 'w', encoding='utf-8') as f:
            json.dump(workspace_config, f, indent=2, ensure_ascii=False)
        
        print(f"✓ ワークスペース用MCP設定を作成: {workspace_config_path}")
        print("  このプロジェクト専用の設定です")
        
        return True
        
    except Exception as e:
        print(f"❌ ワークスペース設定の作成エラー: {e}")
        return False

def show_usage_instructions():
    """使用方法の説明を表示"""
    print("\n=== 使用方法 ===")
    print("1. Kiroを再起動してMCPサーバーを認識させる")
    print("2. または、コマンドパレットで 'MCP Server' を検索して再接続")
    print("3. チャットで以下のように使用:")
    print("   - 'プロジェクトのルールを記録して' → add_note_to_memory")
    print("   - '以前の決定事項を検索して' → search_memory")
    print("   - 'プロジェクトルールを確認して' → get_project_rules")
    print("   - 'すべてのメモリを表示して' → list_all_memories")
    
    print("\n=== 利用可能なツール ===")
    tools = [
        ("add_note_to_memory", "メモリにノートを追加"),
        ("search_memory", "キーワードまたはタグでメモリを検索"),
        ("update_memory_entry", "既存のメモリエントリを更新"),
        ("delete_memory_entry", "メモリエントリを削除"),
        ("list_all_memories", "すべてのメモリエントリを一覧表示"),
        ("get_project_rules", "プロジェクトルールタグ付きメモリを取得")
    ]
    
    for tool, description in tools:
        print(f"  - {tool}: {description}")

if __name__ == "__main__":
    success = add_memory_server_to_kiro()
    if success:
        create_workspace_config()
        show_usage_instructions()
        print("\n✅ Memory Server MCPの統合が完了しました！")
    else:
        print("\n❌ 統合に失敗しました")