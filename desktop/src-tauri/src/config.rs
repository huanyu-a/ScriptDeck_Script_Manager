//! 配置读写。配置存放在系统应用数据目录，首次运行时尝试从旧版
//! Flask 项目（含 main.py + config.json 的祖先目录）迁移。

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use tauri::Manager;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default)]
    pub scan_root: String,
    #[serde(default)]
    pub exclude_dirs: Vec<String>,
    #[serde(default)]
    pub exclude_bats: Vec<String>,
    #[serde(default)]
    pub exclude_scripts: Vec<String>,
}

impl Default for Config {
    fn default() -> Self {
        let default_root = if cfg!(windows) {
            "C:\\project".to_string()
        } else {
            std::env::var("HOME").unwrap_or_default()
        };
        Config {
            scan_root: default_root,
            exclude_dirs: vec![
                "node_modules".into(),
                ".git".into(),
                "__pycache__".into(),
                "venv".into(),
                ".idea".into(),
            ],
            exclude_bats: vec!["start_*".into()],
            exclude_scripts: vec![],
        }
    }
}

pub fn config_path(app: &tauri::AppHandle) -> Option<PathBuf> {
    app.path()
        .app_data_dir()
        .ok()
        .map(|dir| dir.join("config.json"))
}

pub fn load(app: &tauri::AppHandle) -> Config {
    let Some(path) = config_path(app) else {
        return Config::default();
    };
    if path.exists() {
        if let Ok(text) = fs::read_to_string(&path) {
            if let Ok(cfg) = serde_json::from_str::<Config>(&text) {
                return cfg;
            }
        }
    }

    // 首次运行：先尝试从旧版 Flask 项目迁移，否则用默认值
    let cfg = migrate_from_legacy().unwrap_or_default();
    save(app, &cfg);
    cfg
}

/// 旧版配置迁移：向上查找包含 main.py + config.json 的目录（仅开发环境可命中）。
fn migrate_from_legacy() -> Option<Config> {
    let mut dir = std::env::current_dir().ok()?;
    loop {
        let candidate = dir.join("config.json");
        if candidate.exists() && dir.join("main.py").exists() {
            if let Ok(text) = fs::read_to_string(&candidate) {
                if let Ok(cfg) = serde_json::from_str::<Config>(&text) {
                    return Some(cfg);
                }
            }
            return None;
        }
        if !dir.pop() {
            return None;
        }
    }
}

pub fn save(app: &tauri::AppHandle, cfg: &Config) {
    let Some(path) = config_path(app) else { return };
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    if let Ok(text) = serde_json::to_string_pretty(cfg) {
        let _ = fs::write(&path, text);
    }
}
