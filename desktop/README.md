# ScriptDeck Desktop（Tauri 2 + Rust）

ScriptDeck 的跨平台桌面版，Windows 与 macOS 通用。后端用 Rust 重写（替代 Flask），
前端完全复用仓库根目录的 `templates/` + `static/`。

## 与旧版（Python/Flask）的差异

| 项 | 旧版 | 桌面版 |
|---|---|---|
| 后端 | Python Flask（HTTP API） | Rust Tauri 命令（IPC） |
| 脚本类型 | `.bat` / `.vbs` / `.sh`（同左） | 三端统一 `.bat` / `.vbs` / `.sh` |
| 运行方式 | `.bat` 新开 cmd 窗口（chcp 65001），`.vbs` 用 wscript.exe，`.sh` 用 Git Bash 新窗口 | 同左；macOS `.sh` 在 Terminal.app 打开 |
| 配置位置 | 仓库根目录 `config.json` | 系统应用数据目录（首次启动自动从旧版迁移） |
| 打开文件夹 | `explorer` | Windows: `explorer` / macOS: `open` |

- 配置路径：Windows `%APPDATA%\com.scriptdeck.app\config.json`，macOS
  `~/Library/Application Support/com.scriptdeck.app/config.json`
- 扫描规则与旧版**完全一致**（vbs > bat > sh 优先、排除规则、readme 多编码、内嵌元数据解析），
  已通过与 `main.py` 输出逐行 diff 验证。
- `.sh` 在 Windows 上通过 Git Bash（自动定位，不会误用 WSL 的 bash）在新控制台窗口运行，
  脚本结束后保留交互 bash；macOS 上需 `chmod +x` 一次以便 Terminal 直接执行。

## 开发

前置要求：Node 18+、Rust stable（Windows 需 MSVC 工具链）、WebView2（Win11 自带）。

```bash
cd desktop
npm install
npm run sync-ui   # 从根目录 templates/+static/ 同步并改写 UI 到 ui/
npm run dev       # 开发调试窗口
```

> `ui/` 由 `scripts/sync-ui.mjs` 生成（去 Jinja、fetch→invoke、追加 .sh 徽章），
> 不要手改——修改根目录源文件后重新执行 `sync-ui` 即可。

## 版本与发版

版本号**单一来源**是仓库根目录的 `VERSION` 文件，`npm run sync-version` 将其同步到
`tauri.conf.json` / `package.json` / `Cargo.toml`。

发版流程：修改 `VERSION`（如 `1.1.0`）→ 提交并推送到 master → CI 自动打包并发布
同名 GitHub Release（附全平台安装包）。**只有 VERSION 变更（或 Actions 页手动触发）才会打包**，
普通代码推送不触发。

## 打包

```bash
npm run build     # Windows 出 NSIS/MSI；macOS 出 .app/.dmg
```

CI（`.github/workflows/desktop-build.yml`）覆盖 Windows x64 与 macOS universal（Intel + Apple Silicon
双架构单包，无需 Intel runner）；macOS 构建无法在 Windows 上本地执行。

## 目录结构

```
desktop/
├── package.json           # tauri CLI 脚本
├── scripts/sync-ui.mjs    # UI 同步与 Tauri 化改写（幂等）
├── ui/                    # 生成的前端（frontendDist）
└── src-tauri/
    ├── tauri.conf.json
    ├── capabilities/default.json
    └── src/
        ├── main.rs        # 命令注册（与 Flask 端点同构的 JSON 返回）
        ├── config.rs      # 配置读写 + 旧版配置迁移
        ├── scanner.rs     # 扫描 + 元数据解析（含对比测试，cargo test）
        └── runner.rs      # 脚本执行 / 打开文件夹（平台分支）
```
