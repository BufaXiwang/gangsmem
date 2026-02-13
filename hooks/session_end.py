#!/usr/bin/env python3
"""
SessionEnd Hook: 保存对话日志（简化版）

只记录关键信息：
- 用户的问题
- Claude 的核心回复（摘要）
- 使用的 tools/skills/mcp（只记录名称）
- 不记录 tool 的完整返回结果
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

PLUGIN_DIR = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).parent.parent))
GANGSMEM_DIR = Path.home() / ".gangsmem"
LOGS_DIR = GANGSMEM_DIR / "logs"

sys.path.insert(0, str(PLUGIN_DIR / "lib"))


def log(msg: str):
    """输出日志到 stderr"""
    print(f"[gangsmem] {msg}", file=sys.stderr)


def save_log(session_id: str, messages: list):
    """保存简化的日志"""
    if not messages:
        return

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

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

    # 解析并简化 transcript
    try:
        from transcript import parse_transcript_simplified
        messages = parse_transcript_simplified(transcript_path)
    except Exception as e:
        log(f"Failed to parse transcript: {e}")
        return

    save_log(session_id, messages)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[gangsmem] Fatal error: {e}", file=sys.stderr)
        sys.exit(0)
