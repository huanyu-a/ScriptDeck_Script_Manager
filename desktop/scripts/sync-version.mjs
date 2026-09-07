/**
 * sync-version.mjs — 将仓库根目录的 VERSION 同步到各配置文件（单一版本源）。
 * CI 打包前与本地发版前执行，保证安装包版本号一致。
 * 幂等：值一致时不改写文件。
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const desktopDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const version = readFileSync(join(desktopDir, "..", "VERSION"), "utf-8").trim();

if (!/^\d+\.\d+\.\d+(-[\w.]+)?$/.test(version)) {
  console.error(`[sync-version] VERSION 内容非法：${version}`);
  process.exit(1);
}

const targets = [
  {
    file: join(desktopDir, "src-tauri", "tauri.conf.json"),
    pattern: /("version"\s*:\s*")[^"]+(")/,
    replace: (v) => `$1${v}$2`,
  },
  {
    file: join(desktopDir, "package.json"),
    pattern: /("version"\s*:\s*")[^"]+(")/,
    replace: (v) => `$1${v}$2`,
  },
  {
    file: join(desktopDir, "src-tauri", "Cargo.toml"),
    pattern: /^(version\s*=\s*")[^"]+(")/m,
    replace: (v) => `$1${v}$2`,
  },
];

for (const { file, pattern, replace } of targets) {
  const name = file.split(/[\\/]/).slice(-2).join("/");
  const text = readFileSync(file, "utf-8").replace(/\r\n/g, "\n");
  if (!pattern.test(text)) {
    console.error(`[sync-version] ${name} 未找到 version 字段`);
    process.exit(1);
  }
  const updated = text.replace(pattern, replace(version));
  if (updated !== text) {
    writeFileSync(file, updated, "utf-8");
    console.log(`[sync-version] ${name}: -> ${version}`);
  } else {
    console.log(`[sync-version] ${name}: 已是 ${version}`);
  }
}
console.log(`[sync-version] 完成，当前版本 ${version}`);
