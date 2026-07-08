"""
批量注入 bat 文件内嵌元数据（:: title: / :: desc:）。
从同一目录的 readme.md 读取标题和描述，插入到 bat 文件的 @echo off 之后。
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import scan_directory, load_config, parse_bat_metadata

def extract_readme_title_and_desc(readme_content: str):
    """从 readme 内容提取标题（第一行非空非 # ）和描述（第二行非空）"""
    lines = [line.strip() for line in readme_content.split("\n")]
    non_empty = [line for line in lines if line]
    
    title = ""
    desc = ""
    
    if non_empty:
        raw_title = non_empty[0]
        # 去掉 markdown 标题标记
        title = raw_title.lstrip("#").strip()
    
    if len(non_empty) > 1:
        raw_desc = non_empty[1]
        # 去掉可能的 markdown 标记
        desc = raw_desc.lstrip("#").strip()
    
    return title, desc

def inject_metadata(bat_path: str, title: str, desc: str):
    """向 bat 文件注入 :: title: 和 :: desc: 注释，返回是否成功"""
    try:
        with open(bat_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return False
    
    lines = content.split("\n")
    
    # 找到 @echo 行
    echo_index = -1
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if stripped.startswith("@echo"):
            echo_index = i
            break
    
    if echo_index == -1:
        # 没有 @echo 行，在文件头添加 @echo off 和注释
        new_lines = ["@echo off"]
        if title:
            new_lines.append(f":: title: {title}")
        if desc:
            new_lines.append(f":: desc: {desc}")
        if lines and lines[0].strip():
            new_lines.append("")
        new_lines.extend(lines)
    else:
        # 在 @echo 行之后插入
        insert_lines = []
        if title:
            insert_lines.append(f":: title: {title}")
        if desc:
            insert_lines.append(f":: desc: {desc}")
        
        new_lines = lines[:echo_index + 1] + insert_lines + lines[echo_index + 1:]
    
    new_content = "\n".join(new_lines)
    
    try:
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception:
        return False

def main():
    cfg = load_config()
    scan_root = cfg.get("scan_root", "C:\\project")
    exclude_dirs = cfg.get("exclude_dirs", [])
    exclude_bats = cfg.get("exclude_bats", [])
    exclude_scripts = cfg.get("exclude_scripts", [])
    
    print(f"扫描目录: {scan_root}")
    items = scan_directory(scan_root, exclude_dirs, exclude_bats, exclude_scripts)
    
    total_bats = 0
    skipped_has_meta = 0
    injected = 0
    failed = []
    
    for item in items:
        readme = item.get("readme")
        if not readme:
            continue
        
        readme_content = readme.get("content", "")
        title_from_readme, desc_from_readme = extract_readme_title_and_desc(readme_content)
        
        if not title_from_readme and not desc_from_readme:
            continue
        
        for bat in item.get("scripts", []):
            # 仅向 .bat 文件注入元数据，跳过 .vbs
            if bat.get("type") != "bat":
                continue
            total_bats += 1
            bat_path = bat.get("path", "")
            
            if not bat_path or not os.path.isfile(bat_path):
                continue
            
            # 检查是否已有元数据
            existing_meta = parse_bat_metadata(bat_path)
            if existing_meta.get("title") or existing_meta.get("desc"):
                skipped_has_meta += 1
                continue
            
            # 注入元数据
            success = inject_metadata(bat_path, title_from_readme, desc_from_readme)
            if success:
                injected += 1
                print(f"  OK  {item['folder']}/{bat['name']}")
            else:
                failed.append(bat_path)
                print(f"  FAIL {item['folder']}/{bat['name']}")
    
    print(f"\n===== 完成 =====")
    print(f"总 bat 文件: {total_bats}")
    print(f"已有元数据(跳过): {skipped_has_meta}")
    print(f"成功注入: {injected}")
    print(f"失败: {len(failed)}")
    
    if failed:
        print("\n修改失败的文件：")
        for f in failed:
            print(f"  {f}")

if __name__ == "__main__":
    main()
