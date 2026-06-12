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

def scan_directory(scan_root: str, exclude_dirs: list, exclude_bats: list = None, exclude_scripts: list = None):
    """
    扫描 scan_root 下的子文件夹，收集 .bat 文件和 readme 文件。
    exclude_scripts: 按完整路径排除的脚本列表。
    返回按文件夹分组的数据结构：
    [
      {
        "folder": "ai\\bacth_ai",
        "folder_name": "bacth_ai",
        "parent": "ai",
        "bats": [{"name": "xxx.bat", "path": "C:\\...\\xxx.bat"}],
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
        readme = None

        for fname in filenames:
            full = os.path.join(dirpath, fname)
            if fname.lower().endswith(".bat"):
                norm_full = os.path.normpath(full).lower()
                if norm_full in exclude_script_set:
                    continue
                if not bat_excluded(fname, exclude_bats or []):
                    bats.append({"name": fname, "path": full})
            elif is_readme(fname):
                try:
                    content = Path(full).read_text(encoding="utf-8", errors="ignore")[:3000]
                except Exception:
                    content = "(无法读取)"
                readme = {"name": fname, "path": full, "content": content}

        if bats or readme:
            parts = Path(rel).parts
            results.append({
                "folder": rel.replace("\\", "/"),
                "folder_name": parts[-1],
                "parent": parts[0] if len(parts) > 1 else "",
                "bats": bats,
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
    """在新窗口中运行 bat 文件"""
    body = request.json or {}
    bat_path = body.get("path", "").strip()
    if not bat_path or not os.path.isfile(bat_path):
        return jsonify({"ok": False, "msg": f"文件不存在：{bat_path}"}), 400
    try:
        bat_dir = os.path.dirname(bat_path)
        # chcp 65001 将 cmd 切换到 UTF-8 编码，避免 bat 中的中文路径乱码
        subprocess.Popen(
            f'start "Running: {os.path.basename(bat_path)}" cmd /k "chcp 65001 >nul && "{bat_path}""',
            shell=True, cwd=bat_dir
        )
        return jsonify({"ok": True, "msg": f"已启动：{os.path.basename(bat_path)}"})
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
