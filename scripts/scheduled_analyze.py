#!/usr/bin/env python3
"""
定时分析脚本 (由 launchd 调用)

功能：
1. 检查未分析的日志
2. 调用 Claude CLI 分析日志
3. 更新状态文件
4. 重建索引
"""

import subprocess
import json
import sys
import os
from pathlib import Path
from datetime import datetime

GANGSMEM_DIR = Path.home() / ".gangsmem"
STATE_FILE = GANGSMEM_DIR / "state.json"
CONFIG_FILE = GANGSMEM_DIR / "config.json"
LOGS_DIR = GANGSMEM_DIR / "logs"
MEMORY_DIR = GANGSMEM_DIR / "memory"
PLUGIN_DIR = Path(__file__).parent.parent


def log(msg: str):
    """输出带时间戳的日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


def get_claude_path() -> str:
    """获取 claude 可执行文件路径"""
    # 优先从环境变量获取
    if os.environ.get("CLAUDE_PATH"):
        return os.environ["CLAUDE_PATH"]

    # 从配置文件获取
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text())
            if config.get("claude_path"):
                return config["claude_path"]
        except Exception:
            pass

    # 默认
    return "claude"


def get_state() -> dict:
    """读取状态文件"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"analyzed_sessions": [], "last_analyzed": None}


def save_state(state: dict):
    """保存状态文件"""
    state["last_analyzed"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def get_pending_logs(state: dict) -> list:
    """获取未分析的日志文件"""
    analyzed = set(state.get("analyzed_sessions", []))
    pending = []

    if not LOGS_DIR.exists():
        return []

    for log_file in LOGS_DIR.rglob("*.jsonl"):
        # 文件名格式: HH-MM-SS_sessionid.jsonl
        session_id = log_file.stem.split("_")[-1][:8]
        if session_id not in analyzed:
            pending.append((log_file, session_id))

    # 按时间排序（旧的优先）
    pending.sort(key=lambda x: x[0].stat().st_mtime)

    return pending


def analyze_batch(pending: list, state: dict) -> bool:
    """分析一批日志"""
    # 每次最多分析 5 个，避免超时
    batch = pending[:5]

    log_paths = "\n".join(f"- {p[0]}" for p in batch)

    session_ids = ", ".join(s for _, s in batch)

    prompt = f"""
你是一个知识管理助手。请分析以下对话日志，提取可复用的知识点。

## 日志文件
{log_paths}

## 本次分析的 Session IDs
{session_ids}

## 任务流程

### 第一步：读取并分析日志
使用 Read 工具读取上述日志文件，识别有价值的知识点：
- 解决的问题和方案
- 可泛化的技巧、模式、最佳实践
- 重要的代码片段或命令
- 工具使用方法和配置

### 第二步：检查现有记忆
使用 Glob 工具列出 {MEMORY_DIR}/*.md 所有现有文档。
对于每个提取的知识点，判断是否与现有文档相关（通过标题、关键词判断）。

### 第三步：更新或创建文档

**情况 A：找到相关文档 → 更新**
1. 使用 Read 读取现有文档
2. 使用 Edit 工具更新文档：
   - 在 frontmatter 的 `sources` 列表中添加新的 session ID
   - 更新 `updated` 日期为 {datetime.now().strftime("%Y-%m-%d")}
   - 在 `keywords` 中添加新的关键词（如果有）
   - 在文档正文中追加新的内容（使用 "## 补充" 或整合到现有章节）
   - 如果新内容与现有内容重复，则整合去重
   - 如果新内容是对现有内容的补充或修正，直接修改原文

**情况 B：没有相关文档 → 创建新文档**
使用 Write 工具创建新文档，格式如下：

```markdown
---
id: document-id-in-english
title: 文档标题
keywords: [关键词1, 关键词2, 关键词3]
created: {datetime.now().strftime("%Y-%m-%d")}
updated: {datetime.now().strftime("%Y-%m-%d")}
sources: [{session_ids}]
---

# 标题

## 核心内容
详细内容...

## 代码示例（如有）
```code
...
```

## 注意事项（如有）
...
```

### 第四步：重建索引
完成所有文档操作后，运行以下命令重建搜索索引：
```bash
python3 {PLUGIN_DIR}/scripts/rebuild_index.py
```

## 重要原则
- 只提取真正有价值、可复用的知识
- 忽略过于具体或一次性的内容
- 相似主题必须合并到同一文档，避免碎片化
- 关键词应该是用户可能搜索的词
- 更新文档时保留原有内容的完整性

请开始分析。
"""

    claude_path = get_claude_path()
    log(f"Using claude at: {claude_path}")
    log(f"Analyzing {len(batch)} logs...")

    try:
        result = subprocess.run(
            [
                claude_path,
                "-p", prompt,
                "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash",
                "--max-turns", "30"
            ],
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )

        if result.returncode == 0:
            # 更新已分析列表
            for _, session_id in batch:
                if session_id not in state["analyzed_sessions"]:
                    state["analyzed_sessions"].append(session_id)
            save_state(state)
            log(f"Analysis complete. Processed {len(batch)} sessions.")

            # 输出部分结果
            if result.stdout:
                output = result.stdout
                if len(output) > 1000:
                    output = output[:500] + "\n...\n" + output[-500:]
                log(f"Output:\n{output}")

            return True
        else:
            log(f"Error (exit code {result.returncode}):")
            if result.stderr:
                log(result.stderr[:1000])
            return False

    except subprocess.TimeoutExpired:
        log("Error: Analysis timed out after 10 minutes")
        return False
    except Exception as e:
        log(f"Error: {e}")
        return False


def main():
    log("=" * 50)
    log("Starting scheduled analysis...")

    # 确保目录存在
    GANGSMEM_DIR.mkdir(exist_ok=True)
    MEMORY_DIR.mkdir(exist_ok=True)

    state = get_state()
    pending = get_pending_logs(state)

    if not pending:
        log("No pending logs to analyze.")
        return

    log(f"Found {len(pending)} pending logs.")

    # 分批处理
    success = analyze_batch(pending, state)

    if success and len(pending) > 5:
        log(f"Note: {len(pending) - 5} more logs will be analyzed in the next run.")

    log("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
