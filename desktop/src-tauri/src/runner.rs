//! 脚本执行与文件夹打开，按平台分支：
//! - Windows：.vbs 用 wscript.exe；.bat 开新 cmd 窗口（chcp 65001 防 UTF-8 乱码）；
//!   .sh 用 Git Bash 开新控制台窗口（脚本结束后保留交互 bash）
//! - macOS：.sh 在 Terminal.app 中打开；文件夹用 open
//! - Linux：.sh 交给 sh 后台执行；文件夹用 xdg-open

use serde_json::{json, Value};
use std::path::Path;
use std::process::Command;

#[cfg(windows)]
use std::path::PathBuf;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

/// 外层引导进程（cmd /C start）隐藏窗口
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

fn spawn(mut cmd: Command) -> Result<(), String> {
    cmd.spawn().map(|_| ()).map_err(|e| e.to_string())
}

/// 通过 `cmd /C start` 在新控制台窗口运行目标程序。
/// 必须经 start 中转：Rust spawn 默认继承父进程 stdio，而 Tauri 是 GUI 进程
/// 没有有效 stdio，直接 CREATE_NEW_CONSOLE 会让 bash/cmd 读到 EOF 立即退出（闪退）；
/// start 创建的进程才会拿到新控制台自己的 stdin/stdout/stderr。
#[cfg(windows)]
fn spawn_in_new_console(program: &str, args: &[&str], cwd: &Path, title: &str) -> Result<(), String> {
    let mut cmd = Command::new("cmd");
    cmd.arg("/C")
        .arg("start")
        .arg(title)
        .arg(program)
        .args(args)
        .current_dir(cwd)
        .creation_flags(CREATE_NO_WINDOW);
    spawn(cmd)
}

/// Windows 上定位 Git Bash（避免误用 WSL 的 System32\bash.exe，二者路径语义不同）
#[cfg(windows)]
fn find_bash() -> Option<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();
    for var in ["ProgramFiles", "ProgramFiles(x86)", "LocalAppData"] {
        if let Ok(base) = std::env::var(var) {
            let mut dir = PathBuf::from(&base);
            if var == "LocalAppData" {
                dir.push("Programs");
            }
            candidates.push(dir.join("Git/bin/bash.exe"));
        }
    }
    // git.exe 同级推断（Git\cmd\git.exe → Git\bin\bash.exe）
    if let Ok(output) = Command::new("where").arg("git").output() {
        if let Ok(text) = String::from_utf8(output.stdout) {
            if let Some(first) = text.lines().next() {
                let git = PathBuf::from(first.trim());
                if let Some(parent) = git.parent() {
                    candidates.push(parent.join("bin/bash.exe"));
                    candidates.push(parent.join("usr/bin/bash.exe"));
                }
            }
        }
    }
    candidates.into_iter().find(|p| p.is_file())
}

/// Windows 路径 → Git Bash 风格路径（D:\a b\x.sh → /d/a b/x.sh）
#[cfg(windows)]
fn to_unix_path(path: &str) -> String {
    let normalized = path.replace('/', "\\");
    let bytes = normalized.as_bytes();
    if bytes.len() >= 2 && bytes[1] == b':' {
        let drive = (normalized.as_bytes()[0] as char).to_ascii_lowercase();
        format!("/{}{}", drive, &normalized[2..].replace('\\', "/"))
    } else {
        normalized.replace('\\', "/")
    }
}

pub fn run_script(script_path: &str) -> Value {
    let path = Path::new(script_path);
    if !path.is_file() {
        return json!({ "ok": false, "msg": format!("文件不存在：{}", script_path) });
    }
    let ext = path
        .extension()
        .map(|e| e.to_string_lossy().to_lowercase())
        .unwrap_or_default();
    let dir = path.parent().unwrap_or(Path::new("."));
    let basename = path
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_default();

    let result = if cfg!(windows) {
        match ext.as_str() {
            "vbs" => {
                // wscript 是 GUI 子系统，无需控制台，直接启动
                let mut cmd = Command::new("wscript.exe");
                cmd.arg(path).current_dir(dir);
                spawn(cmd)
            }
            "sh" => {
                #[cfg(windows)]
                {
                    let Some(bash) = find_bash() else {
                        return json!({
                            "ok": false,
                            "msg": "未找到 Git Bash，请安装 Git for Windows 后重试"
                        });
                    };
                    // 脚本结束后 exec 进入交互 bash，保持窗口打开（对齐原 .bat 的 cmd /k 行为）
                    let payload = format!(
                        "bash '{}'; exec bash --login",
                        to_unix_path(script_path).replace('\'', "'\\''")
                    );
                    spawn_in_new_console(
                        &bash.to_string_lossy(),
                        &["--login", "-c", &payload],
                        dir,
                        &format!("Running: {}", basename),
                    )
                }
                #[cfg(not(windows))]
                {
                    let mut cmd = Command::new("sh");
                    cmd.arg(path).current_dir(dir);
                    spawn(cmd)
                }
            }
            _ => {
                #[cfg(windows)]
                {
                    // chcp 65001 将 cmd 切换到 UTF-8 编码，避免 bat 中的中文路径乱码
                    let inner = format!("chcp 65001 >nul && \"{}\"", path.display());
                    spawn_in_new_console(
                        "cmd",
                        &["/K", &inner],
                        dir,
                        &format!("Running: {}", basename),
                    )
                }
                #[cfg(not(windows))]
                Err("macOS/Linux 不支持运行 .bat/.vbs，请使用 .sh 脚本".to_string())
            }
        }
    } else if cfg!(target_os = "macos") {
        let mut cmd = Command::new("open");
        cmd.args(["-a", "Terminal"]).arg(path).current_dir(dir);
        spawn(cmd)
    } else {
        // Linux：无统一终端方案，直接后台执行（输出丢弃）
        let mut cmd = Command::new("sh");
        cmd.arg(path).current_dir(dir);
        spawn(cmd)
    };

    match result {
        Ok(()) => json!({ "ok": true, "msg": format!("已启动：{}", basename) }),
        Err(e) => json!({ "ok": false, "msg": e }),
    }
}

pub fn open_folder(folder: &str) -> Value {
    if !Path::new(folder).is_dir() {
        return json!({ "ok": false, "msg": "文件夹不存在" });
    }
    #[cfg(windows)]
    let cmd = {
        let mut c = Command::new("explorer");
        c.arg(folder);
        c
    };
    #[cfg(target_os = "macos")]
    let cmd = {
        let mut c = Command::new("open");
        c.arg(folder);
        c
    };
    #[cfg(all(unix, not(target_os = "macos")))]
    let cmd = {
        let mut c = Command::new("xdg-open");
        c.arg(folder);
        c
    };
    match spawn(cmd) {
        Ok(()) => json!({ "ok": true }),
        Err(e) => json!({ "ok": false, "msg": e }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unix_path_conversion() {
        assert_eq!(to_unix_path(r"D:\project\ai\x.sh"), "/d/project/ai/x.sh");
        assert_eq!(to_unix_path(r"D:\a b\smoke test.sh"), "/d/a b/smoke test.sh");
        assert_eq!(
            to_unix_path(r"D:\project/ai/mixed\slash.sh"),
            "/d/project/ai/mixed/slash.sh"
        );
        assert_eq!(to_unix_path("C:\\ProgramData\\p.exe"), "/c/ProgramData/p.exe");
    }
}
