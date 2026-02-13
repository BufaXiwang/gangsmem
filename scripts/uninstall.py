#!/usr/bin/env python3
"""卸载 launchd 定时任务"""

import subprocess
import sys
from pathlib import Path

PLIST_PATH = Path.home() / "Library/LaunchAgents/com.gangsmem.analyze.plist"


def uninstall() -> bool:
    """卸载 launchd 定时任务"""
    if not PLIST_PATH.exists():
        print("gangsmem: Scheduled task not installed")
        return True

    # 卸载
    result = subprocess.run(
        ["launchctl", "unload", str(PLIST_PATH)],
        capture_output=True,
        text=True
    )

    # 删除文件
    try:
        PLIST_PATH.unlink()
        print("gangsmem: Scheduled task removed")
        return True
    except Exception as e:
        print(f"Error: Failed to remove plist - {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = uninstall()
    sys.exit(0 if success else 1)
