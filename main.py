"""
ScriptDeck - Python 脚本导航器（原 Python Script Navigator）
轻量级 Web 启动台，自动扫描指定目录下的 .bat 文件和 README 文件，提供快速启动入口。
"""

import json
import os
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory

app = Flask(__name__)

CONFIG_PATH = Path(__file__).parent / "config.json"

# ─── 配置管理 ─────────────────────────────────────────────────────────────────

def load_config():
    if not CONFIG_PATH.exists():
        default = {"scan_root": "C:\\project", "exclude_dirs": ["node_modules", ".git", "__pycache__", "venv", ".idea"], "exclude_bats": ["start_*"], "exclude_scripts": [], "host": "127.0.0.1", "port": 5000}
        save_config(default)
        return default
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

CFG = load_config()

# ─── 扫描逻辑 ─────────────────────────────────────────────────────────────────

README_NAMES = {"readme", "readme.md", "readme.txt", "readme.rst", "说明.md", "说明.txt"}

def is_readme(name: str) -> bool:
    return name.lower() in README_NAMES or name.lower().startswith("readme")

def bat_excluded(name: str, exclude_bats: list) -> bool:
    """检查 bat 文件名是否匹配任一排除规则（支持 * ? % 通配符）"""
    if not exclude_bats:
        return False
    lower_name = name.lower()
    for pattern in exclude_bats:
        # % 兼容 SQL 风格通配符，转为 fnmatch 的 *
        pat = pattern.replace("%", "*").lower()
        if fnmatch(lower_name, pat):
            return True
    return False

PREFIXES = ("::", "REM", "rem")

# Windows 常见编码，按优先级排列
BAT_ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb2312", "gb18030"]

def _read_file_with_encoding(filepath: str, max_lines: int = 10):
    """尝试多种编码读取文件前 N 行，返回 (lines_list, used_encoding)。"""
    raw_bytes = b""
    try:
        with open(filepath, "rb") as f:
            for _ in range(max_lines):
                line = f.readline()
                if not line:
                    break
                raw_bytes += line
    except Exception:
        return [], ""

    # 按优先级尝试解码
    for enc in BAT_ENCODINGS:
        try:
            text = raw_bytes.decode(enc)
            lines = [line.rstrip("\r\n") for line in text.split("\n")]
            return lines, enc
        except (UnicodeDecodeError, UnicodeError):
            continue

    # 最终回退：用 errors='replace'
    text = raw_bytes.decode("utf-8", errors="replace")
    return [line.rstrip("\r\n") for line in text.split("\n")], "utf-8-fallback"

def parse_bat_metadata(bat_path: str) -> dict:
    """
    解析 bat 文件头部的内嵌元数据。

    支持的元数据格式：
      @echo off
      :: title: 脚本标题
      :: desc: 脚本描述

    或：
      @echo off
      REM title: 脚本标题
      REM desc: 脚本描述

    :: 和 REM 两种注释风格均可被识别，且可混合使用。

    规则：
      - 第一行必须以 @echo 开头
      - 从第二行开始匹配连续的注释行（以 :: 或 REM 开头）
      - 遇到非注释行就停止
      - 返回 {"title": "...", "desc": "..."}，未匹配到则返回空字符串
    """
    meta = {"title": "", "desc": ""}
    lines, _ = _read_file_with_encoding(bat_path, max_lines=10)

    if not lines:
        return meta

    # 第一行必须以 @echo 开头
    first_line = lines[0].strip().lower()
    if not first_line.startswith("@echo"):
        return meta

    # 从第二行开始解析连续的注释块
    for line in lines[1:]:
        stripped = line.strip()
        detected_prefix = None
        for p in PREFIXES:
            if stripped.startswith(p):
                detected_prefix = p
                break
        if detected_prefix is None:
            break  # 遇到非注释行，停止解析

        content = stripped[len(detected_prefix):].strip()  # 去掉 :: 或 REM 前缀
        if ":" in content:
            key, _, value = content.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "title" and value:
                meta["title"] = value
            elif key == "desc" and value:
                meta["desc"] = value

    return meta


def parse_vbs_metadata(vbs_path: str) -> dict:
    """
    解析 vbs 文件头部的内嵌元数据。

    支持的元数据格式（VBS 使用单引号注释）：
      ' title: 脚本标题
      ' desc: 脚本描述

    规则：
      - 从第一行开始匹配连续的注释行（以 ' 开头）
      - 遇到非注释行就停止
      - 返回 {"title": "...", "desc": "..."}，未匹配到则返回空字符串
    """
    meta = {"title": "", "desc": ""}
    lines, _ = _read_file_with_encoding(vbs_path, max_lines=10)

    if not lines:
        return meta

    # 从第一行开始解析连续的注释块
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("'"):
            break  # 遇到非注释行，停止解析

        content = stripped[1:].strip()  # 去掉 ' 前缀
        if ":" in content:
            key, _, value = content.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "title" and value:
                meta["title"] = value
            elif key == "desc" and value:
                meta["desc"] = value

    return meta


def scan_directory(scan_root: str, exclude_dirs: list, exclude_bats: list = None, exclude_scripts: list = None):
    """
    扫描 scan_root 下的子文件夹，收集 .bat / .vbs 文件和 readme 文件。
    exclude_scripts: 按完整路径排除的脚本列表。
    当同一目录同时存在 .vbs 和 .bat 时，只保留 .vbs（VBS 优先）。
    返回按文件夹分组的数据结构：
    [
      {
        "folder": "ai\\bacth_ai",
        "folder_name": "bacth_ai",
        "parent": "ai",
        "scripts": [{"name": "xxx.bat", "path": "C:\\...\\xxx.bat", "type": "bat", "meta": {"title": "...", "desc": "..."}}],
        "readme": {"name": "readme.md", "path": "...", "content": "..."}
      }
    ]
    """
    root = Path(scan_root)
    if not root.exists():
        return []

    exclude_set = set(exclude_dirs)
    exclude_script_set = set(os.path.normpath(p).lower() for p in (exclude_scripts or []))
    results = []

    for dirpath, dirnames, filenames in os.walk(root):
        # 过滤排除目录（原地修改，阻止 os.walk 深入）
        dirnames[:] = [d for d in dirnames if d not in exclude_set and not d.startswith(".")]

        rel = os.path.relpath(dirpath, root)
        if rel == ".":
            continue

        bats = []
        vbs_scripts = []
        readme = None

        for fname in filenames:
            full = os.path.join(dirpath, fname)
            lower_name = fname.lower()
            if lower_name.endswith(".bat"):
                norm_full = os.path.normpath(full).lower()
                if norm_full in exclude_script_set:
                    continue
                if not bat_excluded(fname, exclude_bats or []):
                    meta = parse_bat_metadata(full)
                    bats.append({"name": fname, "path": full, "meta": meta, "type": "bat"})
            elif lower_name.endswith(".vbs"):
                norm_full = os.path.normpath(full).lower()
                if norm_full in exclude_script_set:
                    continue
                if not bat_excluded(fname, exclude_bats or []):
                    meta = parse_vbs_metadata(full)
                    vbs_scripts.append({"name": fname, "path": full, "meta": meta, "type": "vbs"})
            elif is_readme(fname):
                try:
                    # 尝试多种编码读取 readme，避免中文乱码
                    raw = Path(full).read_bytes()
                    content_text = None
                    for enc in BAT_ENCODINGS:
                        try:
                            content_text = raw[:30000].decode(enc)
                            break
                        except (UnicodeDecodeError, UnicodeError):
                            continue
                    if content_text is None:
                        content_text = raw[:30000].decode("utf-8", errors="replace")
                    content = content_text[:3000]
                except Exception:
                    content = "(无法读取)"
                readme = {"name": fname, "path": full, "content": content}

        # VBS 优先：同目录同时存在 .vbs 和 .bat 时，只保留 .vbs
        scripts = vbs_scripts if vbs_scripts else bats

        if scripts or readme:
            parts = Path(rel).parts
            results.append({
                "folder": rel.replace("\\", "/"),
                "folder_name": parts[-1],
                "parent": parts[0] if len(parts) > 1 else "",
                "scripts": scripts,
                "readme": readme,
            })

    # 按 folder 排序
    results.sort(key=lambda x: x["folder"].lower())
    return results

# ─── 路由 ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/logo.png")
def logo():
    return send_from_directory(os.path.join(app.root_path, "templates"), "logo.png")

@app.route("/api/scan")
def api_scan():
    global CFG
    CFG = load_config()
    data = scan_directory(CFG["scan_root"], CFG.get("exclude_dirs", []), CFG.get("exclude_bats", []), CFG.get("exclude_scripts", []))
    return jsonify({"scan_root": CFG["scan_root"], "items": data, "total": len(data), "exclude_scripts": CFG.get("exclude_scripts", [])})

@app.route("/api/set-root", methods=["POST"])
def api_set_root():
    """修改扫描根目录"""
    global CFG
    body = request.json or {}
    new_root = body.get("scan_root", "").strip()
    if not new_root:
        return jsonify({"ok": False, "msg": "路径不能为空"}), 400
    if not os.path.isdir(new_root):
        return jsonify({"ok": False, "msg": f"路径不存在：{new_root}"}), 400
    CFG["scan_root"] = new_root
    save_config(CFG)
    data = scan_directory(CFG["scan_root"], CFG.get("exclude_dirs", []), CFG.get("exclude_bats", []), CFG.get("exclude_scripts", []))
    return jsonify({"ok": True, "scan_root": new_root, "items": data, "total": len(data)})

@app.route("/api/exclude-bats", methods=["GET", "POST"])
def api_exclude_bats():
    """查询或更新 bat 排除规则"""
    global CFG
    if request.method == "GET":
        return jsonify({"exclude_bats": CFG.get("exclude_bats", [])})
    body = request.json or {}
    patterns = body.get("exclude_bats", [])
    if not isinstance(patterns, list):
        return jsonify({"ok": False, "msg": "exclude_bats 必须是数组"}), 400
    CFG["exclude_bats"] = [p.strip() for p in patterns if p.strip()]
    save_config(CFG)
    data = scan_directory(CFG["scan_root"], CFG.get("exclude_dirs", []), CFG.get("exclude_bats", []), CFG.get("exclude_scripts", []))
    return jsonify({"ok": True, "exclude_bats": CFG["exclude_bats"], "items": data, "total": len(data)})

@app.route("/api/exclude-script", methods=["POST"])
def api_exclude_script():
    """排除或取消排除单个脚本（按完整路径）"""
    global CFG
    body = request.json or {}
    path = body.get("path", "").strip()
    action = body.get("action", "add")  # "add" or "remove"
    if not path:
        return jsonify({"ok": False, "msg": "路径不能为空"}), 400

    exclude_scripts = CFG.get("exclude_scripts", [])
    norm_path = os.path.normpath(path).lower()

    if action == "add":
        if norm_path not in [os.path.normpath(p).lower() for p in exclude_scripts]:
            exclude_scripts.append(path)
    elif action == "remove":
        exclude_scripts = [p for p in exclude_scripts if os.path.normpath(p).lower() != norm_path]

    CFG["exclude_scripts"] = exclude_scripts
    save_config(CFG)
    data = scan_directory(CFG["scan_root"], CFG.get("exclude_dirs", []), CFG.get("exclude_bats", []), CFG.get("exclude_scripts", []))
    return jsonify({"ok": True, "exclude_scripts": CFG["exclude_scripts"], "items": data, "total": len(data)})

@app.route("/api/run-bat", methods=["POST"])
def api_run_bat():
    """运行脚本文件（.bat 或 .vbs）"""
    body = request.json or {}
    script_path = body.get("path", "").strip()
    if not script_path or not os.path.isfile(script_path):
        return jsonify({"ok": False, "msg": f"文件不存在：{script_path}"}), 400
    basename = os.path.basename(script_path)
    try:
        script_dir = os.path.dirname(script_path)
        if script_path.lower().endswith(".vbs"):
            # VBS 通过 wscript.exe 执行，脚本自身控制窗口（如隐藏 GUI）
            subprocess.Popen(f'wscript.exe "{script_path}"', shell=True, cwd=script_dir)
        else:
            # chcp 65001 将 cmd 切换到 UTF-8 编码，避免 bat 中的中文路径乱码
            subprocess.Popen(
                f'start "Running: {basename}" cmd /k "chcp 65001 >nul && "{script_path}""',
                shell=True, cwd=script_dir
            )
        return jsonify({"ok": True, "msg": f"已启动：{basename}"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

@app.route("/api/open-folder", methods=["POST"])
def api_open_folder():
    """在资源管理器中打开文件夹"""
    body = request.json or {}
    folder = body.get("path", "").strip()
    if not folder or not os.path.isdir(folder):
        return jsonify({"ok": False, "msg": "文件夹不存在"}), 400
    try:
        subprocess.Popen(f'explorer "{folder}"', shell=True)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

# ─── 启动 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    host = CFG.get("host", "127.0.0.1")
    port = CFG.get("port", 5000)
    print(f"ScriptDeck 启动中...")
    print(f"扫描目录：{CFG['scan_root']}")
    print(f"访问地址：http://{host}:{port}")
    print("按 Ctrl+C 停止")
    app.run(host=host, port=port, debug=False)
