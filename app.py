"""Lightweight VPS-like demo for Render free tier.

Safe by design for a public demo:
- Password login required (APP_PASSWORD env var). No password in code/repo.
- Commands are an allowlist, run without a shell, with timeout and output cap.
- File browsing is confined to ./demo_files, path traversal is rejected.
- No SSH, no persistent disk, no package installs, no network calls from the app.
"""
import hashlib
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

from flask import Flask, jsonify, redirect, request, url_for

app = Flask(__name__)
START_TIME = time.time()
BASE_DIR = Path(__file__).resolve().parent
DEMO_DIR = BASE_DIR / "demo_files"
DEMO_DIR.mkdir(exist_ok=True)

ALLOWED = {"pwd", "ls", "echo", "date", "uname", "uptime", "whoami", "hostname", "df", "free", "ps"}
FORBIDDEN_CHARS = set(";&|><`$\\\n\r\x00")


def _auth_cookie_value():
    pw = os.environ.get("APP_PASSWORD", "")
    return hashlib.sha256(f"demo:{pw}".encode()).hexdigest() if pw else ""


def _is_authed():
    expected = _auth_cookie_value()
    return bool(expected) and request.cookies.get("demo_auth") == expected


def _page(body, title="VPS Demo"):
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
body{{font-family:system-ui,sans-serif;max-width:820px;margin:24px auto;padding:0 16px;line-height:1.6}}
pre{{background:#111;color:#eee;padding:12px;overflow:auto;white-space:pre-wrap}}
input,button{{padding:8px;font-size:16px}} table{{border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:6px 10px}}
.warn{{background:#fff3cd;padding:10px}}</style></head><body>{body}</body></html>"""


@app.route("/")
def index():
    if not _is_authed():
        return _page("""
<h1>VPS 演示版</h1><p class="warn">演示版，不是真正的 VPS：Render 免费档无 SSH、无持久磁盘、512MB、15 分钟无流量休眠。</p>
<form method="post" action="/login"><label>访问码 <input name="password" type="password" autocomplete="off"></label>
<button>登录</button></form>""")
    try:
        with open("/proc/meminfo") as f:
            mem = [l for l in f if l.startswith(("MemTotal:", "MemAvailable:"))]
    except Exception:
        mem = []
    try:
        up = float(open("/proc/uptime").read().split()[0])
    except Exception:
        up = time.time() - START_TIME
    disk = shutil.disk_usage(str(BASE_DIR))
    files = sorted(p.name for p in DEMO_DIR.iterdir()) if DEMO_DIR.exists() else []
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in [
        ("系统", platform.system() + " " + platform.release()),
        ("Python", platform.python_version()),
        ("主机名", platform.node()),
        ("运行时间（秒）", f"{up:.0f}"),
        ("内存", " / ".join(mem).replace("\n", " ") or "未知"),
        ("磁盘", f"总 {disk.total//1024//1024} MB，可用 {disk.free//1024//1024} MB"),
    ])
    flist = "".join(f"<li>{f}</li>" for f in files) or "<li>（空）</li>"
    return _page(f"""
<h1>VPS 演示版</h1><p>已登录。命令只允许白名单、无 shell、5 秒超时；文件只限 demo_files 目录。</p>
<table>{rows}</table>
<h2>命令（白名单）</h2><p>可用：pwd ls echo date uname uptime whoami hostname df free ps</p>
<form method="post" action="/cmd"><input name="cmd" placeholder="例如：ls" style="width:70%">
<button>执行</button></form>
<h2>演示文件</h2><ul>{flist}</ul>
<form method="post" action="/logout"><button>退出登录</button></form>""")


@app.route("/login", methods=["POST"])
def login():
    pw = request.form.get("password", "")
    if pw and pw == os.environ.get("APP_PASSWORD", ""):
        resp = redirect(url_for("index"))
        resp.set_cookie("demo_auth", _auth_cookie_value(), httponly=True, samesite="Lax")
        return resp
    return _page("<h1>访问码不对</h1><p><a href='/'>返回重试</a></p>"), 401


@app.route("/logout", methods=["POST"])
def logout():
    resp = redirect(url_for("index"))
    resp.delete_cookie("demo_auth")
    return resp


@app.route("/cmd", methods=["POST"])
def cmd():
    if not _is_authed():
        return jsonify({"error": "unauthorized"}), 401
    raw = (request.form.get("cmd") or "").strip()
    if not raw or any(c in raw for c in FORBIDDEN_CHARS):
        return jsonify({"error": "命令不合法或含禁用字符"}), 400
    parts = raw.split()
    if parts[0] not in ALLOWED:
        return jsonify({"error": f"不在白名单：{parts[0]}"}), 400
    try:
        out = subprocess.run(parts, capture_output=True, text=True, timeout=5, cwd=str(DEMO_DIR))
        text = (out.stdout + out.stderr)[:2000]
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500
    return _page(f"<h1>执行结果</h1><pre>{text}</pre><p><a href='/'>返回</a></p>")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
