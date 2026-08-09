"""
开发服务器：自动刷新前端资源版本号 + 监听 code/**/*.py 变更自动重启后端。

用法:
    python scripts/dev_server.py
    python scripts/dev_server.py --port 8088
    python scripts/dev_server.py --host 0.0.0.0 --port 8088
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
INDEX_HTML = FRONTEND_DIR / "index.html"
CODE_DIR = PROJECT_ROOT / "code"


def _file_hash(path: Path) -> str:
    """返回文件内容 sha256 前 8 位。"""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:8]


def refresh_asset_versions():
    """根据静态文件内容 hash 刷新 index.html 中 ?v= 版本号。"""
    if not INDEX_HTML.exists():
        print(f"[dev] 找不到 {INDEX_HTML}，跳过版本刷新", file=sys.stderr)
        return

    html = INDEX_HTML.read_text(encoding="utf-8")

    patterns = [
        ("/static/css/style.css", STATIC_DIR / "css" / "style.css"),
        ("/static/js/utils.js", STATIC_DIR / "js" / "utils.js"),
        ("/static/js/api.js", STATIC_DIR / "js" / "api.js"),
        ("/static/js/charts.js", STATIC_DIR / "js" / "charts.js"),
        ("/static/js/components.js", STATIC_DIR / "js" / "components.js"),
        ("/static/js/app.js", STATIC_DIR / "js" / "app.js"),
    ]

    for asset_path, file_path in patterns:
        if not file_path.exists():
            continue
        file_hash = _file_hash(file_path)
        # 仅替换该资源路径后的 ?v=xxx
        regex = re.compile(rf"({re.escape(asset_path)}\?v=)[^\"'\s]+")
        html = regex.sub(rf"\g<1>{file_hash}", html)

    INDEX_HTML.write_text(html, encoding="utf-8")
    print(f"[dev] 已刷新静态资源版本号: {INDEX_HTML}")


def _start_server(host: str, port: int):
    """启动后端 API 服务作为子进程。"""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [
        sys.executable, "-m", "code.search.api",
        "--host", host, "--port", str(port),
    ]
    return subprocess.Popen(cmd, cwd=str(PROJECT_ROOT), env=env)


def run_dev_server(host: str, port: int):
    """启动开发服务器并监听代码变更自动重启。"""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as exc:
        print(f"[dev] 缺少 watchdog，请执行: python -m pip install watchdog ({exc})", file=sys.stderr)
        sys.exit(1)

    refresh_asset_versions()

    proc = _start_server(host, port)
    print(f"[dev] 后端服务已启动 (pid={proc.pid})，监听 http://{host}:{port}")

    class RestartHandler(FileSystemEventHandler):
        def on_any_event(self, event):
            if event.is_directory:
                return
            if not event.src_path.endswith(".py"):
                return
            # 忽略 __pycache__ 和 pyc 文件
            if "__pycache__" in event.src_path or event.src_path.endswith(".pyc"):
                return
            print(f"[dev] 检测到代码变更: {event.src_path}")
            nonlocal proc
            if proc.poll() is None:
                print(f"[dev] 终止旧服务 (pid={proc.pid})")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            refresh_asset_versions()
            proc = _start_server(host, port)
            print(f"[dev] 新服务已启动 (pid={proc.pid})")

    observer = Observer()
    observer.schedule(RestartHandler(), str(CODE_DIR), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
            if proc.poll() is not None:
                print("[dev] 后端服务意外退出，5 秒后重启...", file=sys.stderr)
                time.sleep(5)
                refresh_asset_versions()
                proc = _start_server(host, port)
    except KeyboardInterrupt:
        print("\n[dev] 正在停止...")
        observer.stop()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    observer.join()


def main():
    parser = argparse.ArgumentParser(description="开发服务器（自动重启 + 缓存失效）")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8088, help="监听端口")
    args = parser.parse_args()
    run_dev_server(args.host, args.port)


if __name__ == "__main__":
    main()
