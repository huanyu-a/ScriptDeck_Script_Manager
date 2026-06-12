# AGENTS.md — ScriptDeck（脚本中台）

## 项目定位

一个轻量级 Windows 脚本启动台。扫描指定目录下所有同时包含 `.bat` 和 `readme.md` 的子目录，在浏览器中提供现代化的查找、预览和一键启动体验。

并非局限于 Python 脚本——任何能通过 `.bat` 启动的项目都能接入。

## 脚本接入规范

ScriptDeck 扫描目录时**只收集同时满足以下两点的子目录**：

1. 目录下至少有一个 `.bat` 文件
2. 目录下存在 `readme.md` 文件

`.bat` 文件建议使用绝对路径（含 Python 解释器路径），避免依赖系统环境变量。`readme.md` 第一行作为脚本标题、第二行作为简要描述。

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
- `scan_directory()` — 递归扫描 `scan_root`，收集每子目录下的 `.bat` 和 `readme.md`
- 执行 bat 时用 `subprocess.Popen` + `cmd /k chcp 65001` 确保 UTF-8 不乱码

API 路由：
| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 渲染主页面 |
| `/api/scan` | GET | 扫描并返回所有脚本数据 |
| `/api/set-root` | POST | 修改扫描根目录 |
| `/api/exclude-bats` | GET/POST | 查询/更新 bat 排除规则 |
| `/api/exclude-script` | POST | 添加/移除脚本排除 |
| `/api/run-bat` | POST | 在新建 cmd 窗口中执行 .bat |
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
      "bats": [{"name": "xxx.bat", "path": "C:\\..."}],
      "readme": {"name": "readme.md", "path": "...", "content": "..."}
    }
  ],
  "total": 1
}
```

## UI 特性

- **Hero** — 居中渐变标题 + 环境光晕背景
- **侧边栏** — 品牌区、搜索框、全部/收藏/最近标签、可折叠目录树
- **脚本卡片** — 渐变 Lucide 图标（按关键词自动匹配）、标题、路径、README 摘要、BAT/README 徽章、运行/收藏按钮
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

- **仅 Windows**：依赖 `.bat`、`cmd`、`explorer.exe`
- 路径使用反斜杠，经 `os.path.normpath` 标准化

## 开发笔记

- 无测试、Linter、CI
- Flask `debug=False`（默认）
- 模板修改需重启服务器；CSS/JS 热重载无需重启
- Lucide 图标名在 `app.js` 的 `iconFor()` 中配置

## 文件结构

```
ScriptDeck/
├── main.py                 # Flask 后端（单文件）
├── config.json             # 运行时配置
├── requirements.txt        # 依赖（仅 Flask）
├── templates/
│   ├── index.html         # 主界面模板
│   └── logo.png           # 品牌 Logo
└── static/
    ├── screenshots/
    │   └── index.png      # 界面截图
    ├── css/
    │   └── app.css        # 完整样式表
    └── js/
        └── app.js         # 前端逻辑
```
