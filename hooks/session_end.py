#!/usr/bin/env python3
"""
SessionEnd Hook: 保存对话日志 + 首次自动配置 launchd

输入 (stdin JSON):
{
    "session_id": "abc123",
    "transcript_path": "/path/to/transcript.jsonl",
    "cwd": "/working/directory",
    "reason": "other"
}

输出: 无 (仅 stderr 日志)
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

PLUGIN_DIR = Path(__file__).parent.parent
GANGSMEM_DIR = Path.home() / ".gangsmem"
LOGS_DIR = GANGSMEM_DIR / "logs"

# 添加 lib 到 path
sys.path.insert(0, str(PLUGIN_DIR / "lib"))


def log(msg: str):
    """输出日志到 stderr"""
    print(f"[gangsmem] {msg}", file=sys.stderr)


def ensure_dirs():
    """确保目录存在"""
    GANGSMEM_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    (GANGSMEM_DIR / "memory").mkdir(exist_ok=True)


def is_launchd_installed() -> bool:
    """检查 launchd 是否已配置"""
    plist = Path.home() / "Library/LaunchAgents/com.gangsmem.analyze.plist"
    return plist.exists()


def ensure_launchd_installed():
    """首次运行时自动配置 launchd"""
    if is_launchd_installed():
        return

    install_script = PLUGIN_DIR / "scripts/install.py"
    if not install_script.exists():
        log(f"Install script not found: {install_script}")
        return

    try:
        result = subprocess.run(
            ["python3", str(install_script)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.stdout:
            log(result.stdout.strip())
        if result.returncode != 0 and result.stderr:
            log(f"Install error: {result.stderr.strip()}")
    except Exception as e:
        log(f"Failed to install launchd: {e}")


def save_log(session_id: str, messages: list):
    """保存简化的日志"""
    if not messages:
        return

    now = datetime.now()
    date_dir = LOGS_DIR / now.strftime("%Y-%m-%d")
    date_dir.mkdir(exist_ok=True)

    filename = f"{now.strftime('%H-%M-%S')}_{session_id[:8]}.jsonl"
    log_file = date_dir / filename

    with open(log_file, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    log(f"Saved {len(messages)} messages to {log_file.name}")


def main():
    # 读取 hook 输入
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        log("Invalid JSON input")
        return

    transcript_path = input_data.get("transcript_path")
    session_id = input_data.get("session_id", "unknown")

    if not transcript_path:
        log("No transcript_path provided")
        return

    # 确保目录存在
    ensure_dirs()

    # 首次运行时配置 launchd
    ensure_launchd_installed()

    # 解析 transcript
    try:
        from transcript import parse_transcript
        messages = parse_transcript(transcript_path)
    except Exception as e:
        log(f"Failed to parse transcript: {e}")
        return

    # 保存日志
    save_log(session_id, messages)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[gangsmem] Fatal error: {e}", file=sys.stderr)
        # 不要以非 0 退出，避免阻塞 Claude Code
        sys.exit(0)
