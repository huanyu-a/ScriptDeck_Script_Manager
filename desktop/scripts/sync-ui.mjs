/**
 * 从仓库根目录的 templates/ + static/ 同步 UI 到 desktop/ui/，
 * 并做 Tauri 化改写（去 Jinja、fetch → invoke、.sh 徽章）。
 * 可重复执行：每次都以根目录最新文件为源重新生成。
 */
import { cpSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const srcHtml = join(root, "templates", "index.html");
const srcStatic = join(root, "static");
const destDir = join(root, "desktop", "ui");
const destHtml = join(destDir, "index.html");
const destStatic = join(destDir, "static");

if (!existsSync(srcHtml) || !existsSync(srcStatic)) {
  console.error(`[sync-ui] 找不到源文件：${srcHtml} / ${srcStatic}`);
  process.exit(1);
}

mkdirSync(destDir, { recursive: true });

// ── 1. index.html：去 Jinja、修正相对路径 ──
// 统一为 LF 再匹配，避免 Windows runner 检出 CRLF 导致多行片段匹配失败
let html = readFileSync(srcHtml, "utf-8").replace(/\r\n/g, "\n");
const htmlReplacements = [
  [`{{ url_for('static', filename='css/app.css') }}`, "static/css/app.css"],
  [`{{ url_for('static', filename='js/vendor/lucide.min.js') }}`, "static/js/vendor/lucide.min.js"],
  [`{{ url_for('static', filename='js/vendor/marked.min.js') }}`, "static/js/vendor/marked.min.js"],
  [`{{ url_for('static', filename='js/app.js') }}`, "static/js/app.js"],
  ["../static/logo.png", "static/logo.png"],
  ["自动扫描 bat / vbs 和 README", "自动扫描 bat / vbs / sh 和 README"],
];
for (const [from, to] of htmlReplacements) {
  if (!html.includes(from)) {
    console.error(`[sync-ui] index.html 未找到预期片段：${from}`);
    process.exit(1);
  }
  html = html.replaceAll(from, to);
}
writeFileSync(destHtml, html, "utf-8");

// ── 2. static/ 原样复制 ──
cpSync(srcStatic, destStatic, { recursive: true });

// ── 3. app.js：fetch → Tauri invoke ──
const appJsPath = join(destStatic, "js", "app.js");
let js = readFileSync(appJsPath, "utf-8").replace(/\r\n/g, "\n");

const jsReplacements = [
  // 头部注入 invoke 桥接
  [
    `const storageKeys = {`,
    `const { invoke } = window.__TAURI__.core;\n\nconst storageKeys = {`,
  ],
  // loadData
  [
    `    const response = await fetch("/api/scan");
    const payload = await response.json();`,
    `    const payload = await invoke("scan");`,
  ],
  // setScanRoot
  [
    `    const response = await fetch("/api/set-root", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scan_root: scanRoot }),
    });
    const payload = await response.json();`,
    `    const payload = await invoke("set_root", { scanRoot });`,
  ],
  // loadExcludeBats
  [
    `    const res = await fetch("/api/exclude-bats");
    const data = await res.json();`,
    `    const data = await invoke("get_exclude_bats");`,
  ],
  // saveExcludeBats
  [
    `    const res = await fetch("/api/exclude-bats", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ exclude_bats: patterns }),
    });
    const data = await res.json();`,
    `    const data = await invoke("set_exclude_bats", { excludeBats: patterns });`,
  ],
  // toggleExcludeScript
  [
    `    const res = await fetch("/api/exclude-script", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: script.path, action }),
    });
    const data = await res.json();`,
    `    const data = await invoke("exclude_script", { path: script.path, action });`,
  ],
  // runScriptById
  [
    `    const response = await fetch("/api/run-bat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: script.path }),
    });
    const payload = await response.json();`,
    `    const payload = await invoke("run_script", { path: script.path });`,
  ],
  // openFolder
  [
    `    await fetch("/api/open-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: folderPath }),
    });`,
    `    await invoke("open_folder", { path: folderPath });`,
  ],
  // .sh 标题后缀剥离
  [
    `scriptFile.name.replace(/\\.(bat|vbs)$/i, "")`,
    `scriptFile.name.replace(/\\.(bat|vbs|sh)$/i, "")`,
  ],
  // 徽章：BAT/VBS/SH 通用化
  [
    `<span class="badge \${script.type === "vbs" ? "vbs" : ""}">\${script.type === "vbs" ? "VBS" : "BAT"}</span>`,
    `<span class="badge \${script.type === "bat" ? "" : script.type}">\${script.type.toUpperCase()}</span>`,
  ],
];

for (const [from, to] of jsReplacements) {
  if (!js.includes(from)) {
    console.error(`[sync-ui] app.js 未找到预期片段：\n${from.slice(0, 120)}...`);
    process.exit(1);
  }
  js = js.replace(from, to);
}
writeFileSync(appJsPath, js, "utf-8");

// ── 4. app.css：追加 .sh 徽章样式（幂等） ──
const cssPath = join(destStatic, "css", "app.css");
let css = readFileSync(cssPath, "utf-8");
if (!css.includes(".badge.sh")) {
  css += `
.badge.sh {
  background: rgba(243, 156, 18, .12);
  color: var(--f-warning, #f39c12);
}
`;
  writeFileSync(cssPath, css, "utf-8");
}

console.log("[sync-ui] UI 已同步到 desktop/ui/");
