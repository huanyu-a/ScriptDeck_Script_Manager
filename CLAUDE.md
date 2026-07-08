# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ScriptDeck（脚本中台）— a lightweight Windows script launcher. It scans a directory tree for subfolders containing a script file (`.bat` or `.vbs`) and `readme.md`, then serves a browser UI to search, preview, and launch them. Not limited to Python — any project runnable via `.bat` / `.vbs` works. When a subfolder has both `.vbs` and `.bat`, only the `.vbs` is kept (VBS priority).

## Commands

```bash
# Install dependency
pip install flask

# Run the server (visit http://127.0.0.1:5000)
python main.py

# Batch-inject bat metadata (:: title: / :: desc:) from readme.md files
python inject_bat_meta.py
```

No test suite, linter, or CI exists. Flask runs with `debug=False`.

## Architecture

### Backend — `main.py` (single file)

- `scan_directory()` — recursive `os.walk` over `scan_root`, collects `.bat`/`.vbs`/`readme.md` per subfolder, applies exclude rules. **VBS priority rule**: when a subfolder has both `.vbs` and `.bat`, only `.vbs` is kept. Returns a sorted list of folder-grouped items, each script carrying a `type` (`"bat"`/`"vbs"`) discriminator.
- `parse_bat_metadata()` — reads the first 10 lines of a `.bat` and extracts `:: title:` / `:: desc:` (or `REM` style) comments immediately after `@echo off`.
- `parse_vbs_metadata()` — reads the first 10 lines of a `.vbs` and extracts `' title:` / `' desc:` comments (VBS single-quote style), stopping at the first non-comment line.
- `_read_file_with_encoding()` — tries `utf-8-sig`, `utf-8`, `gbk`, `gb2312`, `gb18030` to handle Chinese-encoded files; falls back to `utf-8` with `errors='replace'`.
- All mutating APIs (`/api/set-root`, `/api/exclude-bats`, `/api/exclude-script`) write `config.json` then re-scan and return fresh data in one response.
- Global `CFG` dict is reloaded from disk at the start of each stateless request (`/api/scan`) and re-saved after mutations; no in-memory cache drift.

### Frontend — vanilla JS, no framework

- `static/js/app.js` — all client logic: state (`appState`), rendering (`render*`), event delegation, `localStorage` persistence for favorites/recent/theme/view-mode.
- `static/css/app.css` — full stylesheet (~1560 lines), CSS custom-property-driven glassmorphism design system.
- `templates/index.html` — Jinja2 template; vendor libs (Lucide icons, Marked.js) loaded locally from `static/js/vendor/`.

### Title / description resolution priority

When displaying a script card, title and summary are resolved in this order (see `flattenScripts()`):
- **Title**: script meta `title:` → `readme.md` first line → filename (sans `.bat`/`.vbs`)
- **Summary**: script meta `desc:` → first 3 lines of readme joined with `·`

### API routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Render main page |
| `/api/scan` | GET | Reload config, re-scan, return all items |
| `/api/set-root` | POST | Change `scan_root` |
| `/api/exclude-bats` | GET/POST | Query/update script filename exclude patterns |
| `/api/exclude-script` | POST | Add/remove single-script exclusion by full path |
| `/api/run-bat` | POST | Run script — `.bat` in a new `cmd` window (`chcp 65001`), `.vbs` via `wscript.exe` |
| `/api/open-folder` | POST | Open folder in `explorer.exe` |

## Platform Constraints

- **Windows-only**: depends on `.bat`, `.vbs` (`wscript.exe`), `cmd`, `explorer.exe`, and Windows registry (see `add_startup.reg` / `remove_startup.reg`).
- Paths use backslashes, normalized via `os.path.normpath`.
- `startup.vbs` and `add_startup.reg` register a run-on-boot entry using a hardcoded Anaconda Python path — these are local conveniences, not portable.

## Configuration — `config.json`

- `scan_root` — directory to walk.
- `exclude_dirs` — folder names to skip (also skips any dot-prefixed folder in `scan_directory`).
- `exclude_bats` — filename patterns (`*`, `?`, `%`) that filter out script files (applies to both `.bat` and `.vbs`).
- `exclude_scripts` — full paths to exclude specific scripts.

## Dev Notes

- Template edits require a server restart; CSS/JS changes only need a browser refresh.
- Lucide icon names per script are chosen by keyword matching in `iconFor()` (`app.js`); default is `zap`.
- Card colors are a deterministic hash of the folder+filename into a fixed palette (`colorFor()`).
- README content is truncated to 3000 chars server-side; both metadata parsers (bat / vbs) only read the first 10 lines.
- `inject_bat_meta.py` only injects `:: title:`/`:: desc:` into `.bat` files; it skips `.vbs` files (identified by the `type` field).
