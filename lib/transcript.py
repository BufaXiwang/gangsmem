#!/usr/bin/env python3
"""Transcript JSONL 解析工具"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Any


def parse_transcript(transcript_path: str) -> List[Dict]:
    """
    解析 Claude Code 的 transcript JSONL 文件

    Args:
        transcript_path: transcript 文件路径

    Returns:
        简化的消息列表，每条包含 id, ts, role, content, tools(可选)
    """
    path = Path(transcript_path)
    if not path.exists():
        return []

    messages = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")

            if msg_type == "user":
                msg = parse_user_message(obj)
                if msg:
                    messages.append(msg)

            elif msg_type == "assistant":
                msg = parse_assistant_message(obj)
                if msg:
                    messages.append(msg)

    return messages


def parse_user_message(obj: Dict) -> Optional[Dict]:
    """解析用户消息"""
    message = obj.get("message", {})
    content = message.get("content", "")

    if not content:
        return None

    return {
        "id": obj.get("uuid", "")[:8],
        "ts": obj.get("timestamp", ""),
        "role": "user",
        "content": content
    }


def parse_assistant_message(obj: Dict) -> Optional[Dict]:
    """解析 assistant 消息"""
    message = obj.get("message", {})
    content_blocks = message.get("content", [])

    if not content_blocks:
        return None

    # 提取文本内容（跳过 thinking）
    text_parts = []
    tools_used = []

    for block in content_blocks:
        if not isinstance(block, dict):
            continue

        block_type = block.get("type")

        if block_type == "text":
            text = block.get("text", "")
            if text:
                text_parts.append(text)

        elif block_type == "tool_use":
            tool_name = block.get("name", "")
            if tool_name:
                tools_used.append(tool_name)

    # 如果没有文本内容，跳过
    if not text_parts:
        return None

    result = {
        "id": obj.get("uuid", "")[:8],
        "ts": obj.get("timestamp", ""),
        "role": "assistant",
        "content": "\n\n".join(text_parts)
    }

    if tools_used:
        # 去重并保持顺序
        seen = set()
        unique_tools = []
        for t in tools_used:
            if t not in seen:
                seen.add(t)
                unique_tools.append(t)
        result["tools"] = unique_tools

    return result


def extract_conversation_summary(messages: List[Dict], max_chars: int = 2000) -> str:
    """
    提取对话摘要

    Args:
        messages: 消息列表
        max_chars: 最大字符数

    Returns:
        对话摘要文本
    """
    if not messages:
        return ""

    parts = []
    total_chars = 0

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        prefix = "User: " if role == "user" else "Assistant: "
        line = f"{prefix}{content[:500]}"

        if total_chars + len(line) > max_chars:
            break

        parts.append(line)
        total_chars += len(line)

    return "\n\n".join(parts)
