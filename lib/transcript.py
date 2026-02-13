#!/usr/bin/env python3
"""
Transcript JSONL 解析工具

简化版：像人的记忆一样，只记录关键信息
- 用户的问题（完整保留）
- Claude 的回复（完整保留）
- 使用的 tools/skills/mcp（只记录名称）
- 不记录 tool 的返回结果（如文件内容、搜索结果等）
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Set


def parse_transcript_simplified(transcript_path: str) -> List[Dict]:
    """
    解析 transcript，提取简化的对话记录

    Returns:
        简化的消息列表，像人的记忆一样模糊但关键
    """
    path = Path(transcript_path)
    if not path.exists():
        return []

    messages = []
    tools_used: Set[str] = set()
    skills_used: Set[str] = set()
    mcp_used: Set[str] = set()

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
                msg, tools, skills, mcps = parse_assistant_message_simplified(obj)
                if msg:
                    messages.append(msg)
                tools_used.update(tools)
                skills_used.update(skills)
                mcp_used.update(mcps)

    # 添加会话摘要（使用的工具）
    if tools_used or skills_used or mcp_used:
        summary = {
            "type": "session_summary",
            "tools": sorted(tools_used),
            "skills": sorted(skills_used),
            "mcp": sorted(mcp_used)
        }
        messages.append(summary)

    return messages


def parse_user_message(obj: Dict) -> Optional[Dict]:
    """解析用户消息"""
    message = obj.get("message", {})
    content = message.get("content", "")

    if not content:
        return None

    # 用户消息完整保留（通常不会太长）
    return {
        "role": "user",
        "content": content,
        "ts": obj.get("timestamp", "")
    }


def parse_assistant_message_simplified(obj: Dict) -> tuple:
    """
    解析 assistant 消息（简化版）

    Returns:
        (message_dict, tools_set, skills_set, mcp_set)
    """
    message = obj.get("message", {})
    content_blocks = message.get("content", [])

    if not content_blocks:
        return None, set(), set(), set()

    text_parts = []
    tools_used = set()
    skills_used = set()
    mcp_used = set()

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
                # 分类工具
                if tool_name.startswith("mcp__"):
                    mcp_used.add(tool_name)
                elif tool_name == "Skill":
                    # 尝试提取 skill 名称
                    skill_input = block.get("input", {})
                    skill_name = skill_input.get("skill", "unknown")
                    skills_used.add(skill_name)
                else:
                    tools_used.add(tool_name)

    # 如果没有文本内容，跳过
    if not text_parts:
        return None, tools_used, skills_used, mcp_used

    # 合并 Claude 的回复（完整保留）
    full_text = "\n\n".join(text_parts)

    result = {
        "role": "assistant",
        "content": full_text,
        "ts": obj.get("timestamp", "")
    }

    # 只记录这条消息用到的工具名
    msg_tools = tools_used | skills_used | mcp_used
    if msg_tools:
        result["used"] = sorted(msg_tools)

    return result, tools_used, skills_used, mcp_used


# 保留原来的完整解析函数，供其他地方使用
def parse_transcript(transcript_path: str) -> List[Dict]:
    """
    解析完整的 transcript（向后兼容）
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
                msg, _, _, _ = parse_assistant_message_simplified(obj)
                if msg:
                    messages.append(msg)

    return messages
