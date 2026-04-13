#!/usr/bin/env python3
"""ぴよログ可視化 簡易サーバー
使い方: python3 server.py
ブラウザで http://localhost:8765 を開く
dataフォルダに新ファイルを置くと自動で再生成・ブラウザ自動更新
"""
import http.server
import json
import subprocess
import threading
import time
import os
import hashlib
from pathlib import Path

DIR = Path(__file__).parent
DATA_DIR = DIR / "data"
PORT = 8765

# config.json から出力ファイル名を読み込む
_cfg_path = DIR / "config.json"
if _cfg_path.exists():
    with open(_cfg_path, encoding="utf-8") as _f:
        _cfg = json.load(_f)
    HTML_FILE = DIR / _cfg.get("output_filename", "piyolog_viz.html")
else:
    HTML_FILE = DIR / "piyolog_viz.html"

_lock = threading.Lock()
_version = str(time.time())

def regen():
    global _version
    with _lock:
        print("🔄 再生成中...")
        result = subprocess.run(
            ["python3", str(DIR / "piyolog_viz.py")],
            cwd=DIR, capture_output=True, text=True
        )
        if result.returncode == 0:
            _version = str(time.time())
            print("✅ 再生成完了")
        else:
            print("❌ エラー:", result.stderr[-500:] if result.stderr else "")

def watch_data():
    """dataフォルダを監視して変化があれば再生成"""
    def snapshot():
        return {str(f): f.stat().st_mtime for f in DATA_DIR.glob("*.txt")}
    last = snapshot()
    while True:
        time.sleep(3)
        current = snapshot()
        if current != last:
            print(f"📁 変化検知: {DATA_DIR}")
            regen()
            last = snapshot()

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/refresh':
            regen()
            self._text(200, _version)
        elif self.path == '/version':
            self._text(200, _version)
        elif self.path in ('/', '/index.html'):
            self.path = '/chika_growth.html'
            super().do_GET()
        else:
            super().do_GET()

    def _text(self, code, body):
        b = body.encode()
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, fmt, *args):
        if '/version' not in args[0] if args else True:
            print(f"  {args[0] if args else ''}")

if __name__ == '__main__':
    # 初回生成
    regen()
    # ファイル監視スレッド
    t = threading.Thread(target=watch_data, daemon=True)
    t.start()
    os.chdir(DIR)
    print(f"\n🌸 サーバー起動: http://localhost:{PORT}")
    print("  ・dataフォルダに新ファイルを置くと自動更新（約3秒後）")
    print("  ・ブラウザも自動リロードされます")
    print("  ・Ctrl+C で停止\n")
    with http.server.HTTPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()
