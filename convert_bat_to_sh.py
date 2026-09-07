"""
convert_bat_to_sh.py — 将扫描根目录下的 .bat 启动脚本批量改造为 .sh 脚本。

规则：
- 简单脚本（@echo off / 元数据 / cd /d %~dp0 / python 调用 / pause）自动逐行翻译；
- 复杂脚本（conda 激活、交互菜单、wt 多窗口等）使用本文件内嵌的手写移植版本；
- 元数据同步转换：:: title: / REM desc: → # title: / # desc:；
- 行尾统一 LF，macOS/Linux 可直接使用；
- 原 .bat 移入 <扫描根>/.bat-sh-backup/<相对路径>（目录以 . 开头，扫描器会跳过），可随时回退；
- 目标 .sh 已存在时跳过，绝不覆盖。

用法：
    python convert_bat_to_sh.py [--dry-run]
"""

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
with open(ROOT / "config.json", encoding="utf-8") as f:
    _CFG = json.load(f)
SCAN_ROOT = Path(_CFG["scan_root"])
BACKUP_ROOT = SCAN_ROOT / ".bat-sh-backup"
EXCLUDE_DIRS = set(_CFG.get("exclude_dirs", []))

COMPLEX_BAT_ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb2312", "gb18030"]

# ── 复杂脚本的手写移植版（相对扫描根的 sh 路径 → 内容）──
HAND_WRITTEN = {
    "ai/webman_v2/aiman_ask_v3.sh": r"""#!/usr/bin/env bash
# title: AI 问答 V3
# desc: 通用 AI 问答工具 V3，支持单文件交互式批量提问。

cd "$(dirname "$0")" || exit 1

# 激活 conda 环境（原脚本 call conda activate python）
source "C:/ProgramData/anaconda3/etc/profile.d/conda.sh" 2>/dev/null \
  || source "$HOME/anaconda3/etc/profile.d/conda.sh" 2>/dev/null || true
conda activate python 2>/dev/null || true

sleep 3
python aiman_ask_v3.py
""",
    "ai/webman_v2/batch_start-aiman_ask_v4_1.sh": r"""#!/usr/bin/env bash
# title: AI 批量问答 (Role=1)
# desc: 批量启动 AI 问答 V4，使用角色 1 处理 input1 目录下的 Excel 文件。

scriptPath="C:/project/ai/webman_v2/aiman_ask_v4.py"
startDir="C:/project/ai/webman_v2"
roleId=1
inputDir="C:/project/ai/webman_v2/input1"

for f in "$inputDir"/*.xlsx; do
    [ -e "$f" ] || continue
    name="$(basename "$f")"
    echo "Starting Python script for file $name in a new Windows Terminal window"
    wt -d "$startDir" cmd //c "python \"$scriptPath\" \"$name\" $roleId"
done

echo "All file processes initiated."
""",
    "ai/webman_v2/batch_start-aiman_ask_v4_45.sh": r"""#!/usr/bin/env bash
# title: AI 批量问答 (Role=45)
# desc: 批量启动 AI 问答 V4，使用角色 45 处理 input45 目录下的 Excel 文件。

scriptPath="C:/project/ai/webman_v2/aiman_ask_v4.py"
startDir="C:/project/ai/webman_v2"
roleId=45
inputDir="C:/project/ai/webman_v2/input1"

for f in "$inputDir"/*.xlsx; do
    [ -e "$f" ] || continue
    name="$(basename "$f")"
    echo "Starting Python script for file $name in a new Windows Terminal window"
    wt -d "$startDir" cmd //c "python \"$scriptPath\" \"$name\" $roleId"
done

echo "All file processes initiated."
""",
    "ai/webman_v2/batch_start-aiman_ask_v4_55.sh": r"""#!/usr/bin/env bash
# title: AI 批量问答 (Role=55)
# desc: 批量启动 AI 问答 V4，使用角色 55 处理 input55 目录下的 Excel 文件。

scriptPath="C:/project/ai/webman_v2/aiman_ask_v4.py"
startDir="C:/project/ai/webman_v2"
roleId=55
inputDir="C:/project/ai/webman_v2/input1"

for f in "$inputDir"/*.xlsx; do
    [ -e "$f" ] || continue
    name="$(basename "$f")"
    echo "Starting Python script for file $name in a new Windows Terminal window"
    wt -d "$startDir" cmd //c "python \"$scriptPath\" \"$name\" $roleId"
done

echo "All file processes initiated."
""",
    "push/daily_push.sh": r"""#!/usr/bin/env bash
# title: 每日推送调度
# desc: 百度 + Bing URL 推送调度入口，支持 all/bd/bd-daily/bing 模式。
# ============================================================
# 综合推送 - 定时任务调度入口（供 Windows 任务计划程序调用）
# 用法：
#   ./daily_push.sh            -> 默认 all 静默 + 写日志
#   ./daily_push.sh bd         -> 仅百度普通
#   ./daily_push.sh bd-daily   -> 仅百度天级
#   ./daily_push.sh bing       -> 仅 Bing IndexNow
# ============================================================

cd "$(dirname "$0")" || exit 1

# 激活 conda 环境（如不需要可注释掉这两行）
source "C:/ProgramData/anaconda3/etc/profile.d/conda.sh" 2>/dev/null && conda activate python || {
    echo "[ERROR] 激活 conda 环境失败" 1>&2
    exit 1
}

MODE="${1:-all}"

python push_all.py "$MODE" --silent --log
exit $?
""",
    "json_extract/keyword_crawler/fixed_crawler.sh": r"""#!/usr/bin/env bash
# title: 关键词爬虫 (交互菜单)
# desc: 交互式关键词爬虫入口，支持百度/Bing/头条下拉词和相关词采集。

echo 关键词爬虫
echo =====================

echo 选项:
echo 1 = 百度下拉词
echo 2 = 百度相关词
echo 3 = 必应下拉词
echo 4 = 必应相关词
echo 5 = 头条下拉词
echo 6 = 头条相关词
echo 7 = 全部运行

read -r -p '请输入选项 (1-7, 支持多选, 如 "1 3"): ' choice

cd "$(dirname "$0")" || exit 1
PYTHON="C:/ProgramData/anaconda3/envs/python/python.exe"

# 在新的终端窗口中运行（有 Windows Terminal 用 wt，否则退化为当前窗口后台运行）
run_new_window() {
  if command -v wt >/dev/null 2>&1; then
    wt -d "$(pwd -W 2>/dev/null || pwd)" cmd //k "$@"
  else
    "$@" &
  fi
}

contains() { case "$1" in *"$2"*) return 0 ;; *) return 1 ;; esac; }

run_all=0
contains "$choice" 7 && run_all=1

if [ "$run_all" = 1 ]; then
    echo 启动中...
    run_new_window "$PYTHON" -u "main.py" --crawler baidu_dropdown
    run_new_window "$PYTHON" -u "main.py" --crawler baidu_related --proxy
    run_new_window "$PYTHON" -u "main.py" --crawler bing_dropdown
    run_new_window "$PYTHON" -u "main.py" --crawler bing_related --proxy
    run_new_window "$PYTHON" -u "main.py" --crawler toutiao_dropdown
    run_new_window "$PYTHON" -u "main.py" --crawler toutiao_related --proxy
    echo 选择完成
    read -r -p "按回车键退出..."
    exit 0
fi

need_proxy=0
contains "$choice" 2 && need_proxy=1
contains "$choice" 4 && need_proxy=1
contains "$choice" 6 && need_proxy=1

use_proxy=n
if [ "$need_proxy" = 1 ]; then
    read -r -p '是否使用代理? (y/n): ' use_proxy
fi

contains "$choice" 1 && { echo 启动百度下拉词...; run_new_window "$PYTHON" -u "main.py" --crawler baidu_dropdown; }
contains "$choice" 2 && {
    echo 启动百度相关词...
    if [ "$use_proxy" = y ]; then
        run_new_window "$PYTHON" -u "main.py" --crawler baidu_related --proxy
    else
        run_new_window "$PYTHON" -u "main.py" --crawler baidu_related
    fi
}
contains "$choice" 3 && { echo 启动必应下拉词...; run_new_window "$PYTHON" -u "main.py" --crawler bing_dropdown; }
contains "$choice" 4 && {
    echo 启动必应相关词...
    if [ "$use_proxy" = y ]; then
        run_new_window "$PYTHON" -u "main.py" --crawler bing_related --proxy
    else
        run_new_window "$PYTHON" -u "main.py" --crawler bing_related
    fi
}
contains "$choice" 5 && { echo 启动头条下拉词...; run_new_window "$PYTHON" -u "main.py" --crawler toutiao_dropdown; }
contains "$choice" 6 && {
    echo 启动头条相关词...
    if [ "$use_proxy" = y ]; then
        run_new_window "$PYTHON" -u "main.py" --crawler toutiao_related --proxy
    else
        run_new_window "$PYTHON" -u "main.py" --crawler toutiao_related
    fi
}

if ! contains "$choice" 1 && ! contains "$choice" 2 && ! contains "$choice" 3 \
   && ! contains "$choice" 4 && ! contains "$choice" 5 && ! contains "$choice" 6; then
    echo 无效选项: "$choice"
    echo 请用 1-7选择,多个用空格分隔
fi

echo 选择完成
read -r -p "按回车键退出..."
""",
    "reptile/baijiahao/start_baijiahao.sh": r"""#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1

source "C:/ProgramData/anaconda3/etc/profile.d/conda.sh" 2>/dev/null || true
conda activate python 2>/dev/null || true

sleep 3
"C:/ProgramData/anaconda3/envs/python/python.exe" "C:/project/reptile/baijiahao/appendBaijiahao.py"
read -r -p "按回车键退出..."
""",
    "reptile/TraverseCrawler/TraverseCrawler.sh": r"""#!/usr/bin/env bash
# title: 遍历爬虫引擎
# desc: 用于 JSON 数据处理、命令行工具 的脚本工具

cd "$(dirname "$0")" || exit 1

PYTHON_EXE="C:/ProgramData/anaconda3/envs/python/python.exe"
CRAWLER="TraverseCrawler.py"
DEFAULT_PARAMS="--threads 12 --use-proxy --batch-size 20"

# 在新的终端窗口中运行（有 Windows Terminal 用 wt，否则退化为当前窗口后台运行）
run_new_window() {
  if command -v wt >/dev/null 2>&1; then
    wt -d "$(pwd -W 2>/dev/null || pwd)" cmd //k "$@"
  else
    "$@" &
  fi
}

clear
echo
echo ==========================
echo   TraverseCrawler
echo ==========================
echo

# 直接打印菜单
"$PYTHON_EXE" -u -c "import json,glob; [print('  {}. {}'.format(i+1,json.load(open(f,encoding='utf-8')).get('description',''))) for i,f in enumerate(sorted(glob.glob('configs/*.json')))]"

# 解析文件路径映射（序号|文件名）
mapfile -t config_list < <("$PYTHON_EXE" -u -c "import glob,os; [print('{}|{}'.format(i+1,f)) for i,f in enumerate(sorted(glob.glob(os.path.join('configs','*.json'))))]")
count=${#config_list[@]}

echo
echo   0. 退出
echo
echo 支持多选，用逗号分隔，例如: 1,2
echo

read -r -p "请选择配置 [0-${count}]: " choice

if [ "$choice" = "0" ]; then
    echo
    echo 已退出
    echo
    read -r -p "按回车键退出..."
    exit 0
fi

# 将逗号替换为空格，遍历每个选择
running=0
for sel in ${choice//,/ }; do
    if ! [[ "$sel" =~ ^[0-9]+$ ]] || [ "$sel" -gt "$count" ] || [ "$sel" -lt 1 ]; then
        echo
        echo 无效选择: "$sel"
        continue
    fi
    CFG="${config_list[$((sel - 1))]#*|}"
    echo 启动: "$CFG"
    run_new_window "$PYTHON_EXE" -u "$CRAWLER" --config "$CFG" $DEFAULT_PARAMS "$@"
    running=$((running + 1))
done

if [ "$running" -gt 0 ]; then
    echo
    echo 已启动 ${running} 个采集任务，请在各自窗口中查看进度。
else
    echo
    echo 没有有效的选择。
fi
echo
read -r -p "按回车键退出..."
""",
    "tool/ScriptDeck_Script_Manager/startup.sh": r"""#!/usr/bin/env bash
# 供计划任务/注册表后台静默启动旧 Flask 版使用（无窗口，等同原 startup.bat）
cd "$(dirname "$0")" || exit 1

"C:/ProgramData/anaconda3/envs/python/pythonw.exe" "C:/project/tool/ScriptDeck_Script_Manager/main.py"
""",
}


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in COMPLEX_BAT_ENCODINGS:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace")


RISKY_CHARS = set('()&|<>%"^')
CMD_KEYWORDS = ("set", "if ", "if exist", "for ", "goto", "start ", "call ", "errorlevel", "shift")


def translate_simple(bat_path: Path):
    """逐行翻译简单 bat；遇到无法安全翻译的行返回 None（交给手工处理）。"""
    lines = read_text(bat_path).splitlines()
    out = []
    need_script_dir = any("%~dp0" in l for l in lines)
    if need_script_dir:
        out.append('SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"')
    for raw in lines:
        stripped = raw.strip()
        lower = stripped.lower()
        if not stripped or lower.startswith("@echo") or lower.startswith("chcp") or lower == "cls":
            continue
        if stripped.startswith("::"):
            content = stripped[2:].strip()
            out.append(f"# {content}" if content else "#")
            continue
        if lower.startswith("rem"):
            content = stripped[3:].strip()
            out.append(f"# {content}" if content else "#")
            continue
        if lower == "echo.":
            out.append("echo")
            continue
        if lower.startswith("echo ") or lower == "echo":
            rest = stripped[4:].strip()
            if rest and any(c in rest for c in RISKY_CHARS):
                # 括号等特殊字符用双引号包裹（bash 双引号内反斜杠对普通字符无副作用）
                escaped = rest.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
                out.append(f'echo "{escaped}"')
                continue
            out.append(f"echo {rest}".rstrip())
            continue
        if lower in ('cd /d "%~dp0"', "cd /d %~dp0"):
            out.append('cd "$(dirname "$0")" || exit 1')
            continue
        if lower.startswith('cd /d ') and lower.rstrip().endswith('"') and lower.count('"') >= 2:
            expr = stripped[5:].strip().strip('"')
            if "%" in expr.replace("%~dp0", ""):
                return None
            expr = expr.replace("%~dp0", "$SCRIPT_DIR/").replace("\\", "/")
            expr = expr.replace("$SCRIPT_DIR//", "$SCRIPT_DIR/")
            out.append(f'cd "{expr}" || exit 1')
            continue
        if lower == "pause":
            out.append('read -r -p "按回车键退出..."')
            continue
        # 其余视为普通命令行：不允许 cmd 专属语法
        if any(k in lower for k in CMD_KEYWORDS):
            return None
        rest = stripped.replace("%~dp0", "$SCRIPT_DIR/")
        if "%" in rest.replace("%*", "").replace("$SCRIPT_DIR/", ""):
            return None  # %1..%9 等变量不支持
        if rest.count('"') % 2 == 1:
            return None  # 引号不配对
        out.append(rest.replace("\\", "/").replace("%*", '"$@"'))
    return out


def collect_bats():
    bats = []
    for dirpath, dirnames, filenames in os.walk(SCAN_ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.lower().endswith(".bat"):
                bats.append(Path(dirpath) / f)
    return sorted(bats)


def main():
    dry_run = "--dry-run" in sys.argv
    converted, skipped_exist, failed = [], [], []

    for bat in collect_bats():
        rel = bat.relative_to(SCAN_ROOT).as_posix()
        sh_rel = rel[:-4] + ".sh"
        sh_path = SCAN_ROOT / sh_rel

        if sh_path.exists():
            skipped_exist.append(rel)
            continue

        if sh_rel in HAND_WRITTEN:
            content = HAND_WRITTEN[sh_rel]
            source = "hand-written"
        else:
            body = translate_simple(bat)
            if body is None:
                failed.append(rel)
                continue
            content = "#!/usr/bin/env bash\n" + "\n".join(body) + "\n"
            source = "auto"

        if dry_run:
            print(f"[dry-run] {rel} -> {sh_rel} ({source})")
            converted.append(rel)
            continue

        sh_path.parent.mkdir(parents=True, exist_ok=True)
        # 统一 LF 行尾
        sh_path.write_bytes(content.replace("\r\n", "\n").encode("utf-8"))

        backup = BACKUP_ROOT / bat.relative_to(SCAN_ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(bat), str(backup))

        converted.append(rel)
        print(f"[ok] {rel} -> {sh_rel} ({source})")

    print()
    print(f"转换完成：{len(converted)}  跳过(已存在)：{len(skipped_exist)}  无法自动转换：{len(failed)}")
    if skipped_exist:
        print("跳过：", *skipped_exist, sep="\n  ")
    if failed:
        print("无法自动转换（保留 .bat，请手工处理）：", *failed, sep="\n  ")


if __name__ == "__main__":
    main()
