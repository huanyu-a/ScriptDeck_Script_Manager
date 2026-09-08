#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

//! ScriptDeck 桌面版（Tauri 2）。
//! 所有命令的返回 JSON 与旧版 Flask 端点保持同构，前端逻辑无需感知差异。

mod config;
mod runner;
mod scanner;

use serde_json::{json, Value};
use tauri::AppHandle;

fn do_scan(cfg: &config::Config) -> (Vec<scanner::Item>, usize) {
    let items = scanner::scan(
        &cfg.scan_root,
        &cfg.exclude_dirs,
        &cfg.exclude_bats,
        &cfg.exclude_scripts,
    );
    let total = items.len();
    (items, total)
}

/// GET /api/scan
#[tauri::command]
fn scan(app: AppHandle) -> Value {
    let cfg = config::load(&app);
    let (items, total) = do_scan(&cfg);
    json!({
        "scan_root": cfg.scan_root,
        "items": items,
        "total": total,
        "exclude_scripts": cfg.exclude_scripts,
    })
}

/// POST /api/set-root
#[tauri::command]
fn set_root(app: AppHandle, scan_root: String) -> Value {
    let scan_root = scan_root.trim().to_string();
    if scan_root.is_empty() {
        return json!({ "ok": false, "msg": "路径不能为空" });
    }
    if !std::path::Path::new(&scan_root).is_dir() {
        return json!({ "ok": false, "msg": format!("路径不存在：{}", scan_root) });
    }
    let mut cfg = config::load(&app);
    cfg.scan_root = scan_root.clone();
    config::save(&app, &cfg);
    let (items, total) = do_scan(&cfg);
    json!({
        "ok": true,
        "scan_root": scan_root,
        "items": items,
        "total": total,
    })
}

/// GET /api/exclude-bats
#[tauri::command]
fn get_exclude_bats(app: AppHandle) -> Value {
    let cfg = config::load(&app);
    json!({ "exclude_bats": cfg.exclude_bats })
}

/// POST /api/exclude-bats
#[tauri::command]
fn set_exclude_bats(app: AppHandle, exclude_bats: Vec<String>) -> Value {
    let mut cfg = config::load(&app);
    cfg.exclude_bats = exclude_bats
        .into_iter()
        .map(|p| p.trim().to_string())
        .filter(|p| !p.is_empty())
        .collect();
    config::save(&app, &cfg);
    let (items, total) = do_scan(&cfg);
    json!({
        "ok": true,
        "exclude_bats": cfg.exclude_bats,
        "items": items,
        "total": total,
    })
}

/// POST /api/exclude-script
#[tauri::command]
fn exclude_script(app: AppHandle, path: String, action: String) -> Value {
    let path = path.trim().to_string();
    if path.is_empty() {
        return json!({ "ok": false, "msg": "路径不能为空" });
    }

    let mut cfg = config::load(&app);
    let norm = |p: &str| p.replace('\\', "/").to_lowercase();
    let norm_path = norm(&path);

    if action == "add" {
        if !cfg.exclude_scripts.iter().any(|p| norm(p) == norm_path) {
            cfg.exclude_scripts.push(path);
        }
    } else if action == "remove" {
        cfg.exclude_scripts.retain(|p| norm(p) != norm_path);
    }

    config::save(&app, &cfg);
    let (items, total) = do_scan(&cfg);
    json!({
        "ok": true,
        "exclude_scripts": cfg.exclude_scripts,
        "items": items,
        "total": total,
    })
}

/// POST /api/run-bat
#[tauri::command]
fn run_script(path: String) -> Value {
    runner::run_script(path.trim())
}

/// POST /api/open-folder
#[tauri::command]
fn open_folder(path: String) -> Value {
    runner::open_folder(path.trim())
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            use tauri::Manager;
            use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
            use tauri::tray::TrayIconBuilder;
            // Windows/Linux 去掉原生标题栏，由前端自绘 mac 红绿灯接管窗口控制；
            // macOS 保留原生窗口（titleBarStyle Overlay，红绿灯融入顶栏）
            #[cfg(any(windows, target_os = "linux"))]
            {
                if let Some(win) = app.get_webview_window("main") {
                    let _ = win.set_decorations(false);
                }
            }
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.show();
            }

            // 系统托盘：常驻通知区，关窗不退出，只能从托盘菜单真正退出
            let show_item = MenuItem::with_id(app, "show", "显示主界面", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let sep = PredefinedMenuItem::separator(app)?;
            let tray_menu = Menu::with_items(app, &[&show_item, &sep, &quit_item])?;
            let _tray = TrayIconBuilder::with_id("main-tray")
                .icon(app.default_window_icon().expect("app icon").clone())
                .menu(&tray_menu)
                .tooltip("ScriptDeck 脚本中台")
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "show" => {
                        if let Some(win) = app.get_webview_window("main") {
                            let _ = win.show();
                            let _ = win.unminimize();
                            let _ = win.set_focus();
                        }
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click { button, .. } = event {
                        if button == tauri::tray::MouseButton::Left {
                            let app = tray.app_handle();
                            if let Some(win) = app.get_webview_window("main") {
                                let _ = win.show();
                                let _ = win.unminimize();
                                let _ = win.set_focus();
                            }
                        }
                    }
                })
                .build(app)?;
            Ok(())
        })
        .on_window_event(|window, event| {
            // 点红键 / 关闭按钮 → 隐藏到托盘而非退出，保证常驻
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .invoke_handler(tauri::generate_handler![
            scan,
            set_root,
            get_exclude_bats,
            set_exclude_bats,
            exclude_script,
            run_script,
            open_folder,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
