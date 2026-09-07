//! 目录扫描与脚本元数据解析。
//! 与旧版 main.py 的 scan_directory / parse_bat_metadata / parse_vbs_metadata
//! 保持 1:1 行为一致，并在非 Windows 平台追加 .sh 支持。

use serde::Serialize;
use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize)]
pub struct ScriptMeta {
    pub title: String,
    pub desc: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct Script {
    pub name: String,
    pub path: String,
    #[serde(rename = "type")]
    pub script_type: String,
    pub meta: ScriptMeta,
}

#[derive(Debug, Clone, Serialize)]
pub struct Readme {
    pub name: String,
    pub path: String,
    pub content: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct Item {
    pub folder: String,
    pub folder_name: String,
    pub parent: String,
    pub scripts: Vec<Script>,
    pub readme: Option<Readme>,
}

/// 三端统一扫描 .bat/.vbs/.sh（对应脚本 type 字段）
fn script_extensions() -> &'static [&'static str] {
    &["bat", "vbs", "sh"]
}

/// 与 Python 版 README_NAMES + startswith("readme") 行为一致
fn is_readme(name: &str) -> bool {
    let lower = name.to_lowercase();
    matches!(
        lower.as_str(),
        "readme.md" | "readme.txt" | "readme.rst" | "说明.md" | "说明.txt"
    ) || lower.starts_with("readme")
}

/// 通配符匹配（* ?），% 视同 *（兼容 SQL 风格），大小写不敏感
fn name_excluded(name: &str, patterns: &[String]) -> bool {
    if patterns.is_empty() {
        return false;
    }
    let lower = name.to_lowercase();
    patterns.iter().any(|p| {
        let pat = p.replace('%', "*").to_lowercase();
        wildmatch::WildMatch::new(&pat).matches(&lower)
    })
}

/// 路径比较用的归一化：分隔符统一为 / 并小写（对齐 Python 的 normpath().lower()）
fn normalize_for_compare(p: &str) -> String {
    p.replace('\\', "/").to_lowercase()
}

/// 多编码读取：BOM → UTF-8 → GB18030（GBK/GB2312 的超集），与旧版 BAT_ENCODINGS 链等价
fn decode_bytes(raw: &[u8]) -> String {
    const UTF8_BOM: &[u8] = b"\xEF\xBB\xBF";
    if raw.starts_with(UTF8_BOM) {
        return String::from_utf8_lossy(&raw[3..]).into_owned();
    }
    if let Ok(text) = std::str::from_utf8(raw) {
        return text.to_string();
    }
    let (decoded, _, _) = encoding_rs::GB18030.decode(raw);
    decoded.into_owned()
}

/// 读取文件前 max_lines 行（按字节读，保证编码处理可控）
fn read_head_lines(path: &Path, max_lines: usize) -> Vec<String> {
    let Ok(raw) = fs::read(path) else {
        return vec![];
    };
    // 只保留前 max_lines 行对应的字节
    let mut newlines = 0;
    let mut end = raw.len();
    for (i, b) in raw.iter().enumerate() {
        if *b == b'\n' {
            newlines += 1;
            if newlines == max_lines {
                end = i + 1;
                break;
            }
        }
    }
    decode_bytes(&raw[..end])
        .lines()
        .map(|l| l.trim_end().to_string())
        .collect()
}

/// .bat 元数据：首行须 @echo，随后连续 :: / REM 注释块中的 title: / desc:
fn parse_bat_metadata(path: &Path) -> ScriptMeta {
    let mut meta = ScriptMeta {
        title: String::new(),
        desc: String::new(),
    };
    let lines = read_head_lines(path, 10);
    if lines.is_empty() {
        return meta;
    }
    if !lines[0].trim().to_lowercase().starts_with("@echo") {
        return meta;
    }
    for line in &lines[1..] {
        let stripped = line.trim();
        let content = if let Some(rest) = stripped.strip_prefix("::") {
            rest.trim()
        } else if let Some(rest) = stripped.strip_prefix("REM").or(stripped.strip_prefix("rem")) {
            rest.trim()
        } else {
            break; // 非注释行，停止解析
        };
        fill_meta(&mut meta, content);
    }
    meta
}

/// .vbs / .sh 元数据：从首行开始连续的单引号 / # 注释块
fn parse_comment_metadata(path: &Path, prefix: &str) -> ScriptMeta {
    let mut meta = ScriptMeta {
        title: String::new(),
        desc: String::new(),
    };
    for line in read_head_lines(path, 10) {
        let stripped = line.trim();
        let Some(content) = stripped.strip_prefix(prefix) else {
            break; // 非注释行，停止解析
        };
        fill_meta(&mut meta, content.trim());
    }
    meta
}

fn fill_meta(meta: &mut ScriptMeta, content: &str) {
    if let Some((key, value)) = content.split_once(':') {
        let key = key.trim().to_lowercase();
        let value = value.trim();
        match (key.as_str(), !value.is_empty()) {
            ("title", true) => meta.title = value.to_string(),
            ("desc", true) => meta.desc = value.to_string(),
            _ => {}
        }
    }
}

fn parse_script_metadata(path: &Path, ext: &str) -> ScriptMeta {
    match ext {
        "bat" => parse_bat_metadata(path),
        "vbs" => parse_comment_metadata(path, "'"),
        "sh" => parse_comment_metadata(path, "#"),
        _ => ScriptMeta {
            title: String::new(),
            desc: String::new(),
        },
    }
}

pub fn scan(
    scan_root: &str,
    exclude_dirs: &[String],
    exclude_bats: &[String],
    exclude_scripts: &[String],
) -> Vec<Item> {
    let root = PathBuf::from(scan_root);
    if !root.is_dir() {
        return vec![];
    }

    let exclude_set: HashSet<&str> = exclude_dirs.iter().map(|s| s.as_str()).collect();
    let exclude_script_set: HashSet<String> = exclude_scripts
        .iter()
        .map(|p| normalize_for_compare(p))
        .collect();
    let exts = script_extensions();

    let mut results: Vec<Item> = Vec::new();

    let walker = walkdir::WalkDir::new(&root)
        .follow_links(false)
        .into_iter()
        .filter_entry(|entry| {
            // 与 Python 版一致：跳过排除目录和 . 开头目录（含根目录本身也能通过）
            let name = entry.file_name().to_string_lossy();
            if entry.depth() > 0 {
                !exclude_set.contains(name.as_ref()) && !name.starts_with('.')
            } else {
                true
            }
        });

    for entry in walker.flatten() {
        if entry.depth() == 0 || !entry.file_type().is_dir() {
            continue;
        }

        let mut bats: Vec<Script> = Vec::new();
        let mut vbs_scripts: Vec<Script> = Vec::new();
        let mut sh_scripts: Vec<Script> = Vec::new();
        let mut readme: Option<Readme> = None;

        let Ok(entries) = fs::read_dir(entry.path()) else {
            continue;
        };
        for dent in entries.flatten() {
            // 只处理文件（目录名可能带 .sh 后缀，如 npm 包 @bomb.sh）
            if !dent.file_type().map(|t| t.is_file()).unwrap_or(false) {
                continue;
            }
            let fname = dent.file_name().to_string_lossy().into_owned();
            let path = dent.path();
            let ext = path
                .extension()
                .map(|e| e.to_string_lossy().to_lowercase())
                .unwrap_or_default();
            let is_script = exts.contains(&ext.as_str());
            if !is_script && !is_readme(&fname) {
                continue;
            }

            let path_str = path.to_string_lossy().into_owned();
            if is_script {
                if exclude_script_set.contains(&normalize_for_compare(&path_str))
                    || name_excluded(&fname, exclude_bats)
                {
                    continue;
                }
                let meta = parse_script_metadata(&path, &ext);
                let script = Script {
                    name: fname,
                    path: path_str,
                    script_type: ext,
                    meta,
                };
                match script.script_type.as_str() {
                    "vbs" => vbs_scripts.push(script),
                    "sh" => sh_scripts.push(script),
                    _ => bats.push(script),
                }
            } else {
                let content = fs::read(&path)
                    .map(|raw| {
                        let raw = &raw[..raw.len().min(30000)];
                        let text = decode_bytes(raw);
                        // 截断到前 3000 字符（按字符边界）
                        let mut end = text.len().min(3000);
                        while end > 0 && !text.is_char_boundary(end) {
                            end -= 1;
                        }
                        text[..end].to_string()
                    })
                    .unwrap_or_else(|_| "(无法读取)".to_string());
                readme = Some(Readme {
                    name: fname,
                    path: path_str,
                    content,
                });
            }
        }

        // 优先级：vbs > bat > sh（历史迁移顺序，兼容存量 vbs/bat 项目）
        let scripts = if !vbs_scripts.is_empty() {
            vbs_scripts
        } else if !bats.is_empty() {
            bats
        } else {
            sh_scripts
        };

        if scripts.is_empty() && readme.is_none() {
            continue;
        }

        let rel = entry
            .path()
            .strip_prefix(&root)
            .map(|p| p.to_string_lossy().replace('\\', "/"))
            .unwrap_or_default();
        let parts: Vec<&str> = rel.split('/').collect();
        let folder_name = parts[parts.len() - 1].to_string();
        let parent = if parts.len() > 1 {
            parts[0].to_string()
        } else {
            String::new()
        };
        results.push(Item {
            folder: rel,
            folder_name,
            parent,
            scripts,
            readme,
        });
    }

    results.sort_by(|a, b| a.folder.to_lowercase().cmp(&b.folder.to_lowercase()));
    results
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 设置 SCAN_ROOT 环境变量后运行：cargo test -- --nocapture
    /// 用于与旧版 Python scan_directory 的输出做一致性对比。
    #[test]
    fn dump_scan_matches_legacy() {
        let root = match std::env::var("SCAN_ROOT") {
            Ok(v) if !v.is_empty() => v,
            _ => {
                eprintln!("SCAN_ROOT 未设置，跳过");
                return;
            }
        };
        let items = scan(&root, &[], &[], &[]);
        for item in &items {
            let scripts: Vec<String> = item
                .scripts
                .iter()
                .map(|s| format!("{}:{}:{}", s.script_type, s.name, s.meta.title))
                .collect();
            println!(
                "{}\treadme={}\t{}",
                item.folder,
                item.readme.as_ref().map(|r| r.name.as_str()).unwrap_or("-"),
                scripts.join(",")
            );
        }
        println!("TOTAL={}", items.len());
    }
}
