#!/usr/bin/env python3
"""
SessionStart Hook: 确保 launchd 定时任务已配置

在 session 开始时检查并安装 launchd 定时任务
"""

import sys
import os
import json
import subprocess
from pathlib import Path

PLUGIN_DIR = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).parent.parent))
GANGSMEM_DIR = Path.home() / ".gangsmem"


def log(msg: str):
    """输出日志到 stderr"""
    print(f"[gangsmem] {msg}", file=sys.stderr)


def is_launchd_installed() -> bool:
    """检查 launchd 是否已配置"""
    plist = Path.home() / "Library/LaunchAgents/com.gangsmem.analyze.plist"
    return plist.exists()


def ensure_dirs():
    """确保目录存在"""
    GANGSMEM_DIR.mkdir(exist_ok=True)
    (GANGSMEM_DIR / "logs").mkdir(exist_ok=True)
    (GANGSMEM_DIR / "memory").mkdir(exist_ok=True)


def install_launchd():
    """安装 launchd 定时任务"""
    install_script = PLUGIN_DIR / "scripts/install.py"
    if not install_script.exists():
        log(f"Install script not found: {install_script}")
        return

    try:
        result = subprocess.run(
            ["bash", "-l", "-c", f'python3 "{install_script}"'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.stdout:
            log(result.stdout.strip())
        if result.returncode != 0 and result.stderr:
            log(f"Install warning: {result.stderr.strip()}")
    except Exception as e:
        log(f"Failed to install launchd: {e}")


def main():
    # 读取 hook 输入
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        pass

    # 确保目录存在
    ensure_dirs()

    # 检查并安装 launchd
    if not is_launchd_installed():
        log("First run - configuring scheduled task...")
        install_launchd()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[gangsmem] Error: {e}", file=sys.stderr)
        sys.exit(0)
