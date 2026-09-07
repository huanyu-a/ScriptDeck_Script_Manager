# AGENTS.md — ScriptDeck（脚本中台）

## 项目定位

一个轻量级 Windows 脚本启动台。扫描指定目录下所有同时包含脚本文件（`.bat` 或 `.vbs`）和 `readme.md` 的子目录，在浏览器中提供现代化的查找、预览和一键启动体验。

并非局限于 Python 脚本——任何能通过 `.bat` / `.vbs` 启动的项目都能接入。

## 桌面版（desktop/）

仓库同时包含 Tauri 2 + Rust 桌面版（`desktop/`），与 Python/Flask 版共存：

- **后端**：`desktop/src-tauri/src/` 下 `config.rs` / `scanner.rs` / `runner.rs` / `main.rs`，是 `main.py` 逻辑的 1:1 移植，命令返回与 Flask 端点**同构的 JSON**
- **前端**：`desktop/ui/` 由 `desktop/scripts/sync-ui.mjs` 从根目录 `templates/` + `static/` 生成（去 Jinja、fetch→`window.__TAURI__.core.invoke`），**不要手改 `ui/`**，改根目录源文件后跑 `npm run sync-ui`
- **脚本类型**：三端统一扫描 `.bat`/`.vbs`/`.sh`（`# title:` 元数据）；`.sh` 运行 Windows 走 Git Bash 新控制台窗口、macOS 走 Terminal.app
- **配置**：存系统应用数据目录（`%APPDATA%\com.scriptdeck.app\config.json`），首次启动自动从旧版根目录 `config.json` 迁移
- 开发 `npm run dev`，打包 `npm run build`；macOS 构建需在 mac 上（或走 `.github/workflows/desktop-build.yml`），详见 `desktop/README.md`
- 一致性回归：`cd desktop/src-tauri && SCAN_ROOT="D:\project" cargo test -- --nocapture` 可与 `main.py` 的扫描输出做逐行对比

## 脚本接入规范

ScriptDeck 扫描目录时**只收集同时满足以下两点的子目录**：

1. 目录下至少有一个 `.bat` / `.vbs` / `.sh` 文件
2. 目录下存在 `readme.md` 文件

**脚本优先规则**：当同一目录同时存在多种脚本时，只保留优先级最高的一类：vbs > bat > sh（历史迁移顺序）。

`.bat` 文件建议使用绝对路径（含 Python 解释器路径），避免依赖系统环境变量。`.vbs` 文件使用 `WScript.Shell` 启动目标程序。`.sh` 文件 Windows 上经 Git Bash 在新控制台窗口运行（脚本结束后保留交互 bash），macOS 上在 Terminal.app 中运行。`readme.md` 第一行作为脚本标题、第二行作为简要描述。

### 内嵌元数据（可选）

脚本文件头部支持内嵌元数据，优先级高于 readme 推导：

- `.bat`：`@echo off` 之后用 `:: title:` / `:: desc:`（或 `REM` 风格）注释
- `.vbs`：用 `' title:` / `' desc:` 单引号注释（VBS 标准注释风格）
- `.sh`：用 `# title:` / `# desc:` 注释

### bat → sh 批量改造

`convert_bat_to_sh.py` 将扫描根下全部 `.bat` 一次性转换为 `.sh`（简单脚本规则翻译、复杂脚本内嵌手写移植、元数据同步转换、LF 行尾），原 `.bat` 移入 `<扫描根>/.bat-sh-backup/` 备份（`.` 开头目录不会被扫描）。已于 2026-09-07 执行完毕，扫描根内现仅存 `.sh`（1 个 `.vbs`）。

## 快速启动

```bash
pip install flask
python main.py
```

访问 `http://127.0.0.1:5000`

## 配置

`config.json`：

| 字段 | 说明 |
|------|------|
| `scan_root` | 扫描根目录，默认 `C:\project` |
| `exclude_dirs` | 排除的文件夹名 |
| `exclude_bats` | 排除的 bat 文件名（支持 `*` `?` `%` 通配符） |
| `exclude_scripts` | 按完整路径排除的脚本 |
| `host` / `port` | Flask 监听地址和端口 |

## 架构

### 后端 (`main.py`)

单文件 Flask 应用。核心逻辑：
- `scan_directory()` — 递归扫描 `scan_root`，收集每子目录下的 `.bat` / `.vbs` 和 `readme.md`；同目录同时存在时只保留 `.vbs`（VBS 优先）
- `parse_bat_metadata()` — 解析 `.bat` 头部的 `:: title:` / `:: desc:` 元数据
- `parse_vbs_metadata()` — 解析 `.vbs` 头部的 `' title:` / `' desc:` 元数据
- 执行脚本：`.bat` 用 `subprocess.Popen` + `cmd /k chcp 65001` 确保 UTF-8 不乱码；`.vbs` 用 `wscript.exe` 执行；`.sh` 用 Git Bash 在新控制台窗口执行（`CREATE_NEW_CONSOLE` + `exec bash --login` 保持窗口）

API 路由：
| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 渲染主页面 |
| `/api/scan` | GET | 扫描并返回所有脚本数据 |
| `/api/set-root` | POST | 修改扫描根目录 |
| `/api/exclude-bats` | GET/POST | 查询/更新脚本文件名排除规则 |
| `/api/exclude-script` | POST | 添加/移除脚本排除 |
| `/api/run-bat` | POST | 执行脚本（.bat 新 cmd 窗口 / .vbs 用 wscript.exe / .sh 用 Git Bash 新窗口） |
| `/api/open-folder` | POST | 在资源管理器中打开文件夹 |

### 前端

- `templates/index.html` — 主界面 Jinja2 模板
- `static/css/app.css` — 完整样式表（~1560 行），CSS 自定义属性驱动的 glassmorphism 设计系统
- `static/js/app.js` — 客户端逻辑：渲染、搜索、收藏、最近运行、详情面板、小火箭按钮
- 图标：Lucide Icons（CDN），Markdown 渲染：Marked.js（CDN）

### API 返回结构

```json
{
  "scan_root": "C:\\project",
  "items": [
    {
      "folder": "ai/bacth_ai",
      "folder_name": "bacth_ai",
      "parent": "ai",
      "scripts": [{"name": "xxx.bat", "path": "C:\\...", "type": "bat", "meta": {"title": "...", "desc": "..."}}],
      "readme": {"name": "readme.md", "path": "...", "content": "..."}
    }
  ],
  "total": 1
}
```

## UI 特性

- **Hero** — 居中渐变标题 + 环境光晕背景
- **侧边栏** — 品牌区、搜索框、全部/收藏/最近标签、可折叠目录树
- **脚本卡片** — 渐变 Lucide 图标（按关键词自动匹配）、标题、路径、README 摘要、BAT/VBS/README 徽章、运行/收藏按钮
- **详情面板** — 点击卡片右侧展示：完整路径、操作按钮、README 渲染、同目录脚本列表
- **小火箭** — 滚动超过 10px 显示，点击触发升空动画后回到顶部
- **收藏 / 最近运行** — `localStorage` 持久化

## 设计系统

- CSS 变量驱动的紫蓝渐变配色：`--accent: #6C5CE7`，`--accent-2: #0984E3`
- Glassmorphism：`rgba` 背景 + `backdrop-filter: blur`
- 字体：PingFang SC → Noto Sans SC → system-ui 逐级回退
- 网格：`repeat(auto-fill, minmax(250px, 1fr))`
- 布局：`.sidebar` 固定，`.content` 独立滚动（`overflow-y: auto`）

## 平台限制

- **旧 Flask 版仅 Windows**：依赖 `.bat`、`.vbs`（`wscript.exe`）、`cmd`、`explorer.exe`；`.sh` 需 Git Bash
- **桌面版**：Windows + macOS；macOS 上 `.bat`/`.vbs` 无法运行，请使用 `.sh`
- 路径使用反斜杠，经 `os.path.normpath` 标准化

## 开发笔记

- 无测试、Linter、CI
- Flask `debug=False`（默认）
- 模板修改需重启服务器；CSS/JS 热重载无需重启
- Lucide 图标名在 `app.js` 的 `iconFor()` 中配置

## 文件结构

```
ScriptDeck/
├── main.py                 # Flask 后端（单文件，含 bat/vbs 元数据解析）
├── inject_bat_meta.py      # 批量注入 bat 元数据（从 readme 读取）
├── config.json             # 运行时配置
├── requirements.txt        # 依赖（仅 Flask）
├── templates/
│   ├── index.html         # 主界面模板
│   └── logo.png           # 品牌 Logo
└── static/
    ├── screenshots/
    │   └── index.png      # 界面截图
    ├── css/
    │   └── app.css        # 完整样式表（含 .badge.vbs）
    └── js/
        └── app.js         # 前端逻辑（scripts + type 字段）
```
