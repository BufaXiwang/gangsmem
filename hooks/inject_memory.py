#!/usr/bin/env python3
"""
UserPromptSubmit Hook: 搜索相关记忆并注入

输入 (stdin JSON):
{
    "session_id": "abc123",
    "prompt": "用户输入的内容",
    "cwd": "/working/directory"
}

输出 (stdout): 相关记忆内容（会被注入到 Claude 上下文）
"""

import sys
import json
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent.parent
GANGSMEM_DIR = Path.home() / ".gangsmem"
CONFIG_FILE = GANGSMEM_DIR / "config.json"

# 添加 lib 到 path
sys.path.insert(0, str(PLUGIN_DIR / "lib"))


def get_config() -> dict:
    """读取配置"""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {
        "auto_inject": True,
        "max_inject_results": 3,
        "max_inject_chars": 1000,
        "use_jieba": False
    }


def main():
    # 读取 hook 输入
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    prompt = input_data.get("prompt", "")
    if not prompt:
        return

    # 读取配置
    config = get_config()
    if not config.get("auto_inject", True):
        return

    # 检查数据库是否存在
    from db import db_exists, search
    if not db_exists():
        return

    # 分词
    from tokenizer import tokenize, build_fts_query
    tokens = tokenize(prompt, use_jieba=config.get("use_jieba", False))
    if not tokens:
        return

    # 构建查询
    query = build_fts_query(tokens, "OR")
    if not query:
        return

    # 搜索
    max_results = config.get("max_inject_results", 3)
    results = search(query, limit=max_results)

    if not results:
        return

    # 输出注入内容
    max_chars = config.get("max_inject_chars", 1000)
    output_inject_content(results, max_chars)


def output_inject_content(results: list, max_chars: int):
    """输出注入内容到 stdout"""
    print("<related-memories>")
    print("以下是可能相关的历史知识，请自行判断是否有用：")
    print()

    total_chars = 0
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        summary = r.get("summary", "")

        # 截断摘要
        remaining = max_chars - total_chars
        if remaining <= 0:
            break

        if len(summary) > remaining:
            summary = summary[:remaining] + "..."

        print(f"[{i}] {title}")
        print(f"    {summary}")
        print()

        total_chars += len(summary)

    print("</related-memories>")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 错误输出到 stderr，不影响 Claude Code
        print(f"[gangsmem] Error: {e}", file=sys.stderr)
        # 正常退出，不阻塞
        sys.exit(0)
