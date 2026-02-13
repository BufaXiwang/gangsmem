#!/usr/bin/env python3
"""
安装 launchd 定时任务

功能：
1. 查找 claude CLI 路径
2. 创建必要目录
3. 生成并加载 launchd plist
"""

import subprocess
import shutil
import json
import sys
from pathlib import Path
from glob import glob

PLIST_NAME = "com.gangsmem.analyze.plist"
PLIST_PATH = Path.home() / "Library/LaunchAgents" / PLIST_NAME
PLUGIN_DIR = Path(__file__).parent.parent
GANGSMEM_DIR = Path.home() / ".gangsmem"


def find_claude_path() -> str:
    """查找 claude 可执行文件的完整路径"""

    # 方法1: shutil.which (当前环境)
    path = shutil.which("claude")
    if path:
        return path

    # 方法2: 常见安装位置
    common_paths = [
        str(Path.home() / ".local/bin/claude"),
        str(Path.home() / ".npm-global/bin/claude"),
        str(Path.home() / ".nvm/versions/node/*/bin/claude"),
        "/usr/local/bin/claude",
        "/opt/homebrew/bin/claude",
        str(Path.home() / ".cargo/bin/claude"),
    ]

    for p in common_paths:
        if "*" in p:
            matches = glob(p)
            for m in matches:
                if Path(m).exists():
                    return m
        elif Path(p).exists():
            return p

    # 方法3: 从用户 shell 获取
    try:
        result = subprocess.run(
            ["bash", "-l", "-c", "which claude"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    raise RuntimeError("Cannot find claude CLI. Please ensure it's installed and in PATH.")


def get_plist_content(claude_path: str) -> str:
    """生成 launchd plist 内容"""
    claude_dir = str(Path(claude_path).parent)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gangsmem.analyze</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{PLUGIN_DIR}/scripts/scheduled_analyze.py</string>
    </array>

    <!-- 每天凌晨 3 点执行 -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <!-- 电脑唤醒后如果错过了就立即执行 -->
    <key>StartCalendarIntervalAllowsOverdueRun</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{GANGSMEM_DIR}/analyze.log</string>

    <key>StandardErrorPath</key>
    <string>{GANGSMEM_DIR}/analyze.err</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{claude_dir}:/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>CLAUDE_PATH</key>
        <string>{claude_path}</string>
        <key>HOME</key>
        <string>{Path.home()}</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>{Path.home()}</string>
</dict>
</plist>
"""


def install() -> bool:
    """安装 launchd 定时任务"""

    # 查找 claude 路径
    try:
        claude_path = find_claude_path()
        print(f"Found claude at: {claude_path}")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

    # 创建目录
    GANGSMEM_DIR.mkdir(exist_ok=True)
    (GANGSMEM_DIR / "logs").mkdir(exist_ok=True)
    (GANGSMEM_DIR / "memory").mkdir(exist_ok=True)
    PLIST_PATH.parent.mkdir(exist_ok=True)

    # 保存配置
    config_file = GANGSMEM_DIR / "config.json"
    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
        except Exception:
            pass

    config["claude_path"] = claude_path
    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False))

    # 如果已存在，先卸载
    if PLIST_PATH.exists():
        subprocess.run(
            ["launchctl", "unload", str(PLIST_PATH)],
            capture_output=True
        )

    # 写入 plist
    PLIST_PATH.write_text(get_plist_content(claude_path))

    # 加载 launchd
    result = subprocess.run(
        ["launchctl", "load", str(PLIST_PATH)],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("gangsmem: Scheduled task configured (daily at 03:00)")
        return True
    else:
        print(f"Error: Failed to load launchd - {result.stderr}", file=sys.stderr)
        return False


def is_installed() -> bool:
    """检查是否已安装"""
    return PLIST_PATH.exists()


if __name__ == "__main__":
    success = install()
    sys.exit(0 if success else 1)
