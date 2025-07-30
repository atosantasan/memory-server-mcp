#!/usr/bin/env python3
"""
Memory Server MCP - GUI Launcher
macOS用のシンプルなGUIランチャー
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import subprocess
import sys
import os
import webbrowser
from pathlib import Path
import time

class MemoryServerLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Memory Server MCP")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # サーバープロセス
        self.server_process = None
        self.server_running = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """UIセットアップ"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # タイトル
        title_label = ttk.Label(main_frame, text="Memory Server MCP", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 説明
        desc_label = ttk.Label(main_frame, 
                              text="Cursor/Claude用の個人メモリサーバー\nMCPプロトコルとREST APIを提供します",
                              justify=tk.CENTER)
        desc_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(0, 20))
        
        # サーバー開始/停止ボタン
        self.start_button = ttk.Button(button_frame, text="サーバー開始", 
                                      command=self.toggle_server, width=15)
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        # ブラウザで開くボタン
        self.browser_button = ttk.Button(button_frame, text="ブラウザで開く", 
                                        command=self.open_browser, width=15,
                                        state=tk.DISABLED)
        self.browser_button.grid(row=0, column=1, padx=(10, 0))
        
        # ステータス
        self.status_label = ttk.Label(main_frame, text="サーバー停止中", 
                                     foreground="red")
        self.status_label.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        # ログ表示
        log_label = ttk.Label(main_frame, text="ログ:")
        log_label.grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=70)
        self.log_text.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # グリッド設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # 終了時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.log("Memory Server MCP Launcher が起動しました")
        
    def log(self, message):
        """ログメッセージを表示"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def toggle_server(self):
        """サーバーの開始/停止を切り替え"""
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()
            
    def start_server(self):
        """サーバーを開始"""
        try:
            self.log("サーバーを開始しています...")
            
            # main.pyのパスを確認
            main_py_path = Path("main.py")
            if not main_py_path.exists():
                self.log("エラー: main.py が見つかりません")
                messagebox.showerror("エラー", "main.py が見つかりません")
                return
            
            # サーバープロセスを開始
            self.server_process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # ログ監視スレッドを開始
            self.log_thread = threading.Thread(target=self.monitor_server_output, daemon=True)
            self.log_thread.start()
            
            # UI更新
            self.server_running = True
            self.start_button.config(text="サーバー停止")
            self.browser_button.config(state=tk.NORMAL)
            self.status_label.config(text="サーバー実行中", foreground="green")
            
            self.log("サーバーが開始されました")
            
            # 少し待ってからブラウザを開く
            self.root.after(3000, self.auto_open_browser)
            
        except Exception as e:
            self.log(f"サーバー開始エラー: {e}")
            messagebox.showerror("エラー", f"サーバーの開始に失敗しました: {e}")
            
    def stop_server(self):
        """サーバーを停止"""
        try:
            self.log("サーバーを停止しています...")
            
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                self.server_process = None
            
            # UI更新
            self.server_running = False
            self.start_button.config(text="サーバー開始")
            self.browser_button.config(state=tk.DISABLED)
            self.status_label.config(text="サーバー停止中", foreground="red")
            
            self.log("サーバーが停止されました")
            
        except subprocess.TimeoutExpired:
            self.log("サーバーの強制終了を実行中...")
            if self.server_process:
                self.server_process.kill()
                self.server_process = None
            self.log("サーバーが強制終了されました")
        except Exception as e:
            self.log(f"サーバー停止エラー: {e}")
            
    def monitor_server_output(self):
        """サーバーの出力を監視"""
        try:
            while self.server_process and self.server_process.poll() is None:
                line = self.server_process.stdout.readline()
                if line:
                    # ログに出力（改行を除去）
                    self.log(line.rstrip())
                    
            # プロセスが終了した場合
            if self.server_running:
                self.log("サーバープロセスが予期せず終了しました")
                self.root.after(0, self.server_stopped_unexpectedly)
                
        except Exception as e:
            self.log(f"ログ監視エラー: {e}")
            
    def server_stopped_unexpectedly(self):
        """サーバーが予期せず停止した場合の処理"""
        self.server_running = False
        self.start_button.config(text="サーバー開始")
        self.browser_button.config(state=tk.DISABLED)
        self.status_label.config(text="サーバー停止中", foreground="red")
        
    def open_browser(self):
        """ブラウザでサーバーを開く"""
        try:
            webbrowser.open("http://localhost:8000")
            self.log("ブラウザでサーバーを開きました")
        except Exception as e:
            self.log(f"ブラウザ起動エラー: {e}")
            messagebox.showerror("エラー", f"ブラウザの起動に失敗しました: {e}")
            
    def auto_open_browser(self):
        """自動でブラウザを開く"""
        if self.server_running:
            self.open_browser()
            
    def on_closing(self):
        """アプリケーション終了時の処理"""
        if self.server_running:
            self.stop_server()
        self.root.destroy()
        
    def run(self):
        """アプリケーションを実行"""
        self.root.mainloop()

def main():
    """メイン関数"""
    try:
        app = MemoryServerLauncher()
        app.run()
    except Exception as e:
        print(f"アプリケーションエラー: {e}")
        messagebox.showerror("エラー", f"アプリケーションの起動に失敗しました: {e}")

if __name__ == "__main__":
    main()