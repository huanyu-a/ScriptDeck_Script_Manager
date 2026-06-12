# ScriptDeck（脚本中台）

> 给你的 Python 脚本一个家 —— 自动扫描目录中的 `.bat` 和 README 文档，在漂亮的浏览器界面中一键查找、预览、启动。不只 Python，任何能用 .bat 跑起来的项目都行。

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)
![Flask](https://img.shields.io/badge/Flask-3.1-orange?logo=flask)

---

## 💡 工作原理

ScriptDeck 不关心你的脚本是什么语言。它只看一件事：**你指定的目录下，哪些子目录同时有 `.bat` 文件和 `readme.md` 文件。**

找到后，自动整理成卡片界面 —— bat 负责启动，readme 负责说明。点一下"运行"，脚本就在新窗口中跑起来了。

### 接入一个新脚本，只需三步

```
你的脚本项目/
├── run.bat         ← 用绝对路径调用脚本（含 Python 解释器路径）
└── readme.md       ← 第一行标题，第二行描述
```

举个例子 —— 假设你有一个 `analysis` 脚本，它的 `run.bat` 长这样：

```bat
@echo off
chcp 65001 >nul
C:\Users\WIN11\.workbuddy\binaries\python\versions\3.13.12\python.exe C:\project\tool\analysis\main.py
```

> ⚠️ **注意**：多 Python 环境下，bat 文件里**必须用绝对路径**指定 Python 解释器，避免跑到系统默认版本。

`readme.md` 长这样：

```md
数据报表分析
读取 Excel 数据并生成周报图表
```

ScriptDeck 会把第一行作为卡片标题，第二行作为描述摘要。后面的内容会完整渲染在详情面板里。

---

## 📸 界面预览

![脚本中台界面截图](static/screenshots/index.png)

---

## ✨ 功能特性

| 特性 | 说明 |
|------|------|
| 🔍 **实时搜索** | 输入即搜，按脚本名或文件夹路径快速过滤 |
| 📁 **目录树导航** | 左侧边栏展示文件夹层级，点击即筛选 |
| ⭐ **收藏夹** | 常用脚本一键收藏，跨会话持久保存 |
| 🕐 **最近运行** | 自动记录最近执行的 5 个脚本 |
| 📄 **README 预览** | 选中脚本后右侧展示 README 内容（Markdown 渲染） |
| 🚀 **一键启动** | 点击"运行"在新 CMD 窗口中启动脚本 |
| 🎨 **现代 UI** | Glassmorphism 毛玻璃设计，紫蓝渐变配色，Lucide 图标 |
| ⬆️ **回到顶部** | 小火箭按钮，带升空动画 |

---

## 🚀 快速开始

### 1. 装依赖

```bash
pip install flask
```

### 2. 启动

```bash
python main.py
```

终端输出：

```
ScriptDeck 启动中...
扫描目录：C:\project
访问地址：http://127.0.0.1:5000
按 Ctrl+C 停止
```

### 3. 使用

- 搜脚本 → 搜索框输入关键词
- 跑脚本 → 点击卡片上的「运行」
- 收藏 → 点卡片上的 ⭐
- 看详情 → 点卡片，右侧面板展开

---

## ⚙️ 配置

`config.json`：

```json
{
  "scan_root": "C:\\project",
  "exclude_dirs": [
    "node_modules", ".git", "__pycache__", "venv", ".idea"
  ],
  "exclude_bats": ["副本", "start_*"],
  "exclude_scripts": [],
  "host": "127.0.0.1",
  "port": 5000
}
```

| 字段 | 说明 |
|------|------|
| `scan_root` | 扫描根目录，改成你自己放脚本的目录 |
| `exclude_dirs` | 跳过这些文件夹 |
| `exclude_bats` | 跳过这些 bat 文件（支持 `*` `?` 通配符） |
| `exclude_scripts` | 按完整路径跳过特定脚本 |
| `host` | 默认 `127.0.0.1`，想局域网访问改成 `0.0.0.0` |
| `port` | 默认 `5000` |

---

## 🖥️ 界面介绍

```
┌─────────────────────────────────────────────────────┐
│                Hero 区域（标题 + 副标题）             │
├────────────┬────────────────────────────────────────┤
│  侧边栏    │          主内容区（脚本卡片网格）         │
│  🔍 搜索  │                                        │
│  全部/收藏 │                                        │
│   /最近    │                                        │
│  📁 目录树 │                                        │
├────────────┴────────────────────────────────────────┤
│           ⬆️ 小火箭（滚动时显示）                    │
└─────────────────────────────────────────────────────┘
```

---

## 📡 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/scan` | GET | 重新扫描目录 |
| `/api/set-root` | POST | 修改扫描根目录 |
| `/api/exclude-bats` | GET/POST | 查询或更新 bat 排除规则 |
| `/api/exclude-script` | POST | 添加/移除脚本排除 |
| `/api/run-bat` | POST | 运行指定 bat 脚本 |
| `/api/open-folder` | POST | 在资源管理器中打开文件夹 |

---

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| 后端 | Python 3.8+, Flask 3.1 |
| 前端 | 原生 JavaScript，零框架 |
| 图标 | Lucide Icons（CDN） |
| Markdown | Marked.js（CDN） |
| 设计 | CSS 自定义属性 + Glassmorphism |
| 运行环境 | 仅 Windows（依赖 .bat / cmd） |

---

## ❓ 常见问题

**Q：bat 运行后窗口出现乱码？**
A：ScriptDeck 启动 bat 时会自动执行 `chcp 65001` 切换到 UTF-8。如果仍有乱码，检查 bat 文件本身的编码。

**Q：怎么让局域网其他电脑也能访问？**
A：把 `config.json` 里的 `host` 改成 `"0.0.0.0"`，重启后用 `http://你电脑IP:5000` 访问。

**Q：改了 HTML 页面没变化？**
A：Flask 模板有缓存，需要重启 `python main.py`。CSS 和 JS 的修改刷新浏览器即可生效。

**Q：怎么排除某个文件夹下所有脚本？**
A：把文件夹名加到 `config.json` 的 `exclude_dirs` 里，重启。

**Q：能自定义脚本图标吗？**
A：当前根据脚本名关键词自动匹配 Lucide 图标。改 `static/js/app.js` 里的 `iconFor()` 函数就行。

**Q：为什么我的脚本没出现在页面上？**
A：检查两点：① 文件夹下是否同时有 `.bat` 和 `readme.md` ② 文件夹是否在 `scan_root` 下且没被 `exclude_dirs` 排除。

---

## 📁 文件结构

```
ScriptDeck/
├── main.py                 # Flask 后端
├── config.json             # 运行时配置
├── requirements.txt        # 依赖
├── AGENTS.md              # AI 项目上下文
├── README.md              # 你正在看的这份文档
├── templates/
│   ├── index.html         # 主界面模板
│   └── logo.png           # 品牌 Logo
└── static/
    ├── screenshots/
    │   └── index.png      # 界面截图
    ├── css/
    │   └── app.css        # 样式表
    └── js/
        └── app.js         # 前端逻辑
```

---

> 用 ❤️ 和 Flask 制作 · 有问题欢迎反馈
