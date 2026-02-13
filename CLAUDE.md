# Gangsmem - Claude Code 记忆增强系统

> 一个基于 Claude Code Plugin 的智能记忆系统，自动记录对话、提取知识、构建索引，并在每次对话时注入相关记忆。

## 技术选型

| 组件 | 方案 | 说明 |
|------|------|------|
| 存储 | 本地文件系统 | ~/.gangsmem/ |
| 搜索索引 | SQLite FTS5 | 全文搜索，零外部依赖 |
| 语义匹配 | Claude 自身判断 | 注入候选记忆，Claude 自行判断相关性 |
| 离线分析 | Claude Skill | /analyze 触发 Claude 分析日志 |
| 分发方式 | Plugin | 一键安装 |

**核心原则：纯本地、零云组件、利用 Claude Code 自身能力**

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code Session                      │
├─────────────────────────────────────────────────────────────┤
│  UserPromptSubmit Hook                                       │
│  ├── 1. 分词提取关键词（jieba/正则）                          │
│  ├── 2. SQLite FTS5 全文搜索                                 │
│  ├── 3. 读取匹配的记忆摘要                                    │
│  └── 4. stdout 注入 → Claude 自己判断是否使用                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  SessionEnd Hook                                             │
│  ├── 读取 transcript_path (完整对话 JSONL)                   │
│  ├── 提取 user/assistant 消息                                │
│  ├── 保存到 logs/{date}/{time}_{session_id}.jsonl           │
│  └── 首次运行时自动配置 launchd 定时任务                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  launchd 定时任务 (每天凌晨 3:00 自动执行)                    │
│  ├── scheduled_analyze.py                                    │
│  │   ├── 检查未分析的日志                                    │
│  │   └── 调用 claude -p "分析..." --allowedTools ...        │
│  ├── Claude CLI 执行分析                                     │
│  │   ├── 读取日志，提取知识点                                 │
│  │   ├── 生成/更新 memory/*.md                               │
│  │   └── 更新 state.json                                     │
│  └── 重建 FTS5 索引                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  /analyze Skill (可选手动触发)                               │
│  └── 立即执行分析，无需等待定时任务                           │
└─────────────────────────────────────────────────────────────┘
```

**用户完全无感知：安装后自动配置，每天自动分析，记忆自动更新。**

### 记忆注入流程

```
用户输入: "claude code hooks 怎么用"
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  inject-memory.py                                            │
│  ├── 分词: ["claude", "code", "hooks", "怎么", "用"]         │
│  ├── FTS5查询: SELECT * FROM memories WHERE memories MATCH ? │
│  └── 返回Top 3 摘要                                          │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  stdout 输出 (注入到 Claude 上下文)                          │
│                                                              │
│  <related-memories>                                          │
│  以下是可能相关的历史知识，请自行判断是否有用：                  │
│                                                              │
│  [1] Claude Code Hooks 指南                                  │
│      SessionEnd hook 可通过 transcript_path 获取完整对话...   │
│                                                              │
│  [2] Hook 开发最佳实践                                       │
│      hook 脚本必须在 5 秒内完成，使用 stderr 输出错误...       │
│  </related-memories>                                         │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
        Claude 自己判断这些记忆是否相关，决定是否使用
```

---

## 数据存储规范

### 目录结构

```
~/.gangsmem/                          # 全局数据目录
├── logs/                             # 对话日志
│   ├── 2026-02-13/                   # 按日期分组
│   │   ├── 11-30-16_d9159daa.jsonl   # {HH-mm-ss}_{session_id前8位}.jsonl
│   │   └── 14-22-05_abc12345.jsonl
│   └── 2026-02-14/
├── memory/                           # 记忆文档 (Markdown)
│   ├── claude-code-hooks.md
│   ├── python-debugging.md
│   └── git-workflows.md
├── search.db                         # SQLite FTS5 索引数据库
├── state.json                        # 处理状态 (已分析的日志)
└── config.json                       # 配置文件
```

### 日志文件格式 (logs/*.jsonl)

从原始 transcript 提取，只保留核心信息：

```json
{"id":"f55bf418","ts":"2026-02-13T11:30:16.889Z","role":"user","content":"用户的问题"}
{"id":"d9700729","ts":"2026-02-13T11:30:28.021Z","role":"assistant","content":"Claude的回复（纯文本，不含thinking）","tools":["Read","Grep"]}
```

### 记忆文档格式 (memory/*.md)

```markdown
---
id: claude-code-hooks
title: Claude Code Hooks 使用指南
keywords: [hooks, claude-code, automation, SessionEnd, UserPromptSubmit]
created: 2026-02-13
updated: 2026-02-13
sources: [d9159daa, abc12345]
---

# Claude Code Hooks 使用指南

## 核心概念

Hooks 是 Claude Code 的生命周期事件处理机制，可在特定事件触发时执行自定义脚本。

## SessionEnd Hook

可以访问 `transcript_path` 获取完整对话 JSONL 文件路径。

```json
{
  "hooks": {
    "SessionEnd": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "python3 session-end.py"
      }]
    }]
  }
}
```

## 注意事项

- hook 脚本必须在超时时间内完成
- 使用 stderr 输出错误日志
- 退出码 0 表示成功
```

### SQLite FTS5 表结构

```sql
-- 记忆文档索引
CREATE VIRTUAL TABLE memories USING fts5(
    id,                    -- 文档ID (文件名不含.md)
    title,                 -- 标题
    keywords,              -- 关键词 (空格分隔)
    content,               -- 全文内容
    summary,               -- 摘要 (前200字)
    tokenize='porter unicode61'  -- 支持英文词干 + Unicode
);

-- 中文分词版本 (如果安装了 jieba)
CREATE VIRTUAL TABLE memories_zh USING fts5(
    id, title, keywords, content, summary,
    tokenize='unicode61'   -- 配合外部分词
);
```

### 状态文件 (state.json)

```json
{
  "last_analyzed": "2026-02-13T14:22:05Z",
  "analyzed_sessions": ["d9159daa", "abc12345"],
  "pending_count": 3,
  "index_version": 1
}
```

### 配置文件 (config.json)

```json
{
  "auto_inject": true,
  "max_inject_results": 3,
  "max_inject_chars": 1000,
  "log_retention_days": 90,
  "use_jieba": false
}
```

---

## Transcript JSONL 格式规范

Claude Code 的 transcript 文件位于 `~/.claude/projects/{project}/{session_id}.jsonl`。

### 消息类型

#### 用户消息 (type: "user")

```json
{
  "type": "user",
  "uuid": "f55bf418-33e8-40c2-9bfe-d3e102e7646f",
  "sessionId": "d9159daa-f6e8-4196-aa24-accab3cc200e",
  "timestamp": "2026-02-13T03:30:16.889Z",
  "message": {
    "role": "user",
    "content": "用户输入的问题内容"
  }
}
```

#### Assistant 消息 (type: "assistant")

```json
{
  "type": "assistant",
  "uuid": "d9700729-c7a2-4afe-8f70-f9ffbec64b9b",
  "parentUuid": "f55bf418-33e8-40c2-9bfe-d3e102e7646f",
  "timestamp": "2026-02-13T03:30:28.021Z",
  "message": {
    "role": "assistant",
    "content": [
      {"type": "thinking", "thinking": "..."},
      {"type": "text", "text": "Claude的回复"},
      {"type": "tool_use", "name": "Read", "input": {...}}
    ]
  }
}
```

---

## Plugin 结构

```
gangsmem/
├── .claude-plugin/
│   └── plugin.json                   # 插件元数据
├── hooks/
│   ├── hooks.json                    # Hook 配置
│   ├── session_end.py                # 保存对话日志 + 首次配置 launchd
│   └── inject_memory.py              # 搜索+注入记忆
├── scripts/
│   ├── install.py                    # 安装 launchd 定时任务
│   ├── uninstall.py                  # 卸载 launchd 定时任务
│   ├── scheduled_analyze.py          # 定时分析脚本 (launchd 调用)
│   └── rebuild_index.py              # 重建 FTS5 索引
├── skills/
│   ├── analyze/
│   │   └── SKILL.md                  # 手动触发分析
│   ├── search/
│   │   └── SKILL.md                  # 深度搜索记忆
│   └── forget/
│       └── SKILL.md                  # 删除记忆
├── lib/
│   ├── __init__.py
│   ├── db.py                         # SQLite FTS5 操作
│   ├── tokenizer.py                  # 分词 (正则/jieba)
│   └── transcript.py                 # 解析 transcript
├── launchd/
│   └── com.gangsmem.analyze.plist    # launchd 配置模板
├── tests/
│   └── ...
└── README.md
```

### plugin.json

```json
{
  "name": "gangsmem",
  "version": "0.1.0",
  "description": "Claude Code 智能记忆增强系统 - 自动记录对话、构建知识库、智能检索",
  "author": "tu",
  "repository": "https://github.com/username/gangsmem",
  "hooks": "hooks/hooks.json"
}
```

### hooks.json

```json
{
  "SessionEnd": [
    {
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "python3 \"${PLUGIN_DIR}/hooks/session_end.py\"",
        "timeout": 30000
      }]
    }
  ],
  "UserPromptSubmit": [
    {
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "python3 \"${PLUGIN_DIR}/hooks/inject_memory.py\"",
        "timeout": 5000
      }]
    }
  ]
}
```

---

## 定时任务设计

### 自动配置流程

```
用户安装 Plugin
       │
       ▼
首次 SessionEnd Hook 触发
       │
       ├── 保存对话日志
       └── 检测 launchd 未配置
           │
           └── 自动运行 scripts/install.py
               ├── 生成 plist 文件
               └── launchctl load 加载任务

每天凌晨 3:00 (launchd 自动触发)
       │
       ▼
scripts/scheduled_analyze.py
       │
       ├── 检查未分析的日志
       ├── 调用 claude -p "分析..."
       ├── Claude 生成/更新记忆文档
       ├── 运行 rebuild_index.py
       └── 更新 state.json
```

### launchd 配置 (macOS)

文件位置: `~/Library/LaunchAgents/com.gangsmem.analyze.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gangsmem.analyze</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${PLUGIN_DIR}/scripts/scheduled_analyze.py</string>
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
    <string>~/.gangsmem/analyze.log</string>
    <key>StandardErrorPath</key>
    <string>~/.gangsmem/analyze.err</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
```

### scripts/install.py

```python
#!/usr/bin/env python3
"""安装 launchd 定时任务（首次 SessionEnd 时自动调用）"""

import subprocess
from pathlib import Path

PLIST_NAME = "com.gangsmem.analyze.plist"
PLIST_PATH = Path.home() / "Library/LaunchAgents" / PLIST_NAME
PLUGIN_DIR = Path(__file__).parent.parent
GANGSMEM_DIR = Path.home() / ".gangsmem"

def find_claude_path() -> str:
    """查找 claude 可执行文件的完整路径"""
    import shutil
    from glob import glob

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
    result = subprocess.run(
        ["bash", "-l", "-c", "which claude"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    raise RuntimeError("Cannot find claude CLI. Please ensure it's installed.")

def get_plist_content(claude_path: str):
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
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StartCalendarIntervalAllowsOverdueRun</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{GANGSMEM_DIR}/analyze.log</string>
    <key>StandardErrorPath</key>
    <string>{GANGSMEM_DIR}/analyze.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{Path(claude_path).parent}:/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>CLAUDE_PATH</key>
        <string>{claude_path}</string>
    </dict>
</dict>
</plist>
"""

def install():
    # 查找 claude 路径
    try:
        claude_path = find_claude_path()
        print(f"✓ Found claude at: {claude_path}")
    except RuntimeError as e:
        print(f"✗ {e}")
        return False

    # 创建目录
    GANGSMEM_DIR.mkdir(exist_ok=True)
    (GANGSMEM_DIR / "logs").mkdir(exist_ok=True)
    (GANGSMEM_DIR / "memory").mkdir(exist_ok=True)
    PLIST_PATH.parent.mkdir(exist_ok=True)

    # 保存 claude 路径到配置
    config_file = GANGSMEM_DIR / "config.json"
    config = {"claude_path": claude_path}
    config_file.write_text(json.dumps(config, indent=2))

    # 如果已存在，先卸载
    if PLIST_PATH.exists():
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)

    # 写入 plist
    PLIST_PATH.write_text(get_plist_content(claude_path))

    # 加载 launchd
    result = subprocess.run(["launchctl", "load", str(PLIST_PATH)], capture_output=True)

    if result.returncode == 0:
        print("✓ gangsmem: 定时任务已配置 (每天 03:00 自动分析)")
        return True
    else:
        print(f"✗ gangsmem: 配置失败 - {result.stderr.decode()}")
        return False

def is_installed():
    return PLIST_PATH.exists()

if __name__ == "__main__":
    install()
```

### scripts/scheduled_analyze.py

```python
#!/usr/bin/env python3
"""定时执行：调用 Claude CLI 分析日志"""

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
PLUGIN_DIR = Path(__file__).parent.parent

def get_claude_path() -> str:
    """获取 claude 可执行文件路径"""
    # 优先从环境变量获取
    if os.environ.get("CLAUDE_PATH"):
        return os.environ["CLAUDE_PATH"]

    # 从配置文件获取
    if CONFIG_FILE.exists():
        config = json.loads(CONFIG_FILE.read_text())
        if config.get("claude_path"):
            return config["claude_path"]

    # 默认
    return "claude"

def log(msg: str):
    print(f"[{datetime.now().isoformat()}] {msg}")

def get_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"analyzed_sessions": [], "last_analyzed": None}

def save_state(state: dict):
    state["last_analyzed"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

def get_pending_logs(state: dict) -> list:
    analyzed = set(state.get("analyzed_sessions", []))
    pending = []

    if not LOGS_DIR.exists():
        return []

    for log_file in LOGS_DIR.rglob("*.jsonl"):
        session_id = log_file.stem.split("_")[-1][:8]
        if session_id not in analyzed:
            pending.append((log_file, session_id))

    return pending

def analyze_batch(pending: list, state: dict):
    """分析一批日志"""
    # 每次最多分析 5 个，避免超时
    batch = pending[:5]

    log_paths = "\n".join(f"- {p[0]}" for p in batch)

    prompt = f"""
你是一个知识管理助手。请分析以下对话日志，提取可复用的知识点。

## 日志文件
{log_paths}

## 任务
1. 使用 Read 工具读取这些日志文件
2. 识别有价值的知识点：
   - 解决的问题和方案
   - 可泛化的技巧、模式、最佳实践
   - 重要的代码片段或命令
3. 对于每个知识点：
   - 检查 ~/.gangsmem/memory/ 是否已有相关文档
   - 有相关文档则更新（追加新内容）
   - 无则创建新文档
4. 文档格式：
   ```markdown
   ---
   id: 文档ID (英文，用于文件名)
   title: 标题
   keywords: [关键词列表]
   created: 创建日期
   updated: 更新日期
   sources: [来源session列表]
   ---

   # 标题

   内容...
   ```
5. 完成后，运行以下命令重建索引：
   python3 {PLUGIN_DIR}/scripts/rebuild_index.py

请开始分析。
"""

    log(f"Analyzing {len(batch)} logs...")

    claude_path = get_claude_path()
    log(f"Using claude at: {claude_path}")

    result = subprocess.run(
        [
            claude_path,
            "-p", prompt,
            "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash",
            "--max-turns", "20"
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
        log(f"Analysis complete. Updated {len(batch)} sessions.")
        return True
    else:
        log(f"Error: {result.stderr[:500]}")
        return False

def main():
    log("Starting scheduled analysis...")

    state = get_state()
    pending = get_pending_logs(state)

    if not pending:
        log("No pending logs to analyze.")
        return

    log(f"Found {len(pending)} pending logs.")

    # 分批处理
    success = analyze_batch(pending, state)

    if success and len(pending) > 5:
        log(f"Note: {len(pending) - 5} more logs will be analyzed tomorrow.")

    log("Done.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
```

### scripts/uninstall.py

```python
#!/usr/bin/env python3
"""卸载 launchd 定时任务"""

import subprocess
from pathlib import Path

PLIST_PATH = Path.home() / "Library/LaunchAgents/com.gangsmem.analyze.plist"

def uninstall():
    if PLIST_PATH.exists():
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True)
        PLIST_PATH.unlink()
        print("✓ gangsmem: 定时任务已移除")
    else:
        print("gangsmem: 定时任务未安装")

if __name__ == "__main__":
    uninstall()
```

---

## Skills 设计

### /analyze - 离线分析

让 Claude 分析未处理的日志，提取知识生成记忆文档。

```markdown
---
name: analyze
description: 分析对话日志，提取知识点生成记忆文档。使用方法：/analyze [--all]
---

## 任务

分析 ~/.gangsmem/logs/ 中未处理的对话日志，提取可复用的知识点。

## 步骤

1. 读取 ~/.gangsmem/state.json 获取已分析的 session 列表
2. 找出未分析的日志文件
3. 分析对话内容，识别：
   - 解决的问题和方案
   - 可泛化的技巧、模式、最佳实践
   - 重要的代码片段或命令
4. 对于每个知识点：
   - 判断是否已有相关记忆文档 → 追加更新
   - 否则创建新文档
5. 更新 state.json
6. 运行 rebuild-index skill 重建索引

## 输出格式

每个记忆文档遵循 memory/*.md 的格式规范（见 CLAUDE.md）。

$ARGUMENTS
```

### /search - 深度搜索

```markdown
---
name: search
description: 深度搜索记忆库。使用方法：/search <query>
---

在 ~/.gangsmem/memory/ 中搜索与查询相关的知识。

## 查询
$ARGUMENTS

## 步骤

1. 使用 SQLite FTS5 搜索 ~/.gangsmem/search.db
2. 读取匹配的记忆文档完整内容
3. 汇总展示给用户
```

### /rebuild-index - 重建索引

```markdown
---
name: rebuild-index
description: 重建 FTS5 搜索索引
---

重建 ~/.gangsmem/search.db 索引：

1. 删除旧的 search.db
2. 扫描 ~/.gangsmem/memory/*.md
3. 解析 frontmatter 和内容
4. 插入 FTS5 表
5. 更新 state.json 的 index_version
```

---

## 核心代码规范

### lib/db.py - SQLite FTS5 操作

```python
import sqlite3
from pathlib import Path
from typing import List, Dict

DB_PATH = Path.home() / ".gangsmem" / "search.db"

def init_db():
    """初始化 FTS5 数据库"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories USING fts5(
            id, title, keywords, content, summary,
            tokenize='porter unicode61'
        )
    """)
    conn.commit()
    return conn

def search(query: str, limit: int = 5) -> List[Dict]:
    """全文搜索"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT id, title, summary,
               bm25(memories) as score
        FROM memories
        WHERE memories MATCH ?
        ORDER BY score
        LIMIT ?
    """, (query, limit))

    results = []
    for row in cursor:
        results.append({
            "id": row[0],
            "title": row[1],
            "summary": row[2],
            "score": row[3]
        })
    return results

def index_document(doc: Dict):
    """索引单个文档"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT OR REPLACE INTO memories(id, title, keywords, content, summary)
        VALUES (?, ?, ?, ?, ?)
    """, (doc["id"], doc["title"], " ".join(doc["keywords"]),
          doc["content"], doc["summary"]))
    conn.commit()
```

### lib/tokenizer.py - 分词

```python
import re
from typing import List

def tokenize_simple(text: str) -> List[str]:
    """简单分词：英文单词 + 中文字符"""
    # 英文单词
    words = re.findall(r'[a-zA-Z][a-zA-Z0-9]*', text.lower())
    # 中文：取2-4字的连续片段
    chinese = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
    return list(set(words + chinese))

def tokenize_jieba(text: str) -> List[str]:
    """jieba 分词（需安装 jieba）"""
    try:
        import jieba
        return list(jieba.cut(text))
    except ImportError:
        return tokenize_simple(text)
```

### hooks/session_end.py

```python
#!/usr/bin/env python3
"""SessionEnd Hook: 保存对话日志 + 首次自动配置 launchd"""

import sys
import json
from pathlib import Path
from datetime import datetime

PLUGIN_DIR = Path(__file__).parent.parent
GANGSMEM_DIR = Path.home() / ".gangsmem"
LOGS_DIR = GANGSMEM_DIR / "logs"

sys.path.insert(0, str(PLUGIN_DIR / "lib"))

def ensure_dirs():
    """确保目录存在"""
    GANGSMEM_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    (GANGSMEM_DIR / "memory").mkdir(exist_ok=True)

def ensure_launchd_installed():
    """首次运行时自动配置 launchd"""
    plist = Path.home() / "Library/LaunchAgents/com.gangsmem.analyze.plist"
    if not plist.exists():
        import subprocess
        result = subprocess.run(
            ["python3", str(PLUGIN_DIR / "scripts/install.py")],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(result.stdout, file=sys.stderr)

def extract_messages(transcript_path: str) -> list:
    """从 transcript 提取消息"""
    from transcript import parse_transcript
    return parse_transcript(transcript_path)

def save_log(session_id: str, messages: list):
    """保存简化的日志"""
    now = datetime.now()
    date_dir = LOGS_DIR / now.strftime("%Y-%m-%d")
    date_dir.mkdir(exist_ok=True)

    filename = f"{now.strftime('%H-%M-%S')}_{session_id[:8]}.jsonl"
    log_file = date_dir / filename

    with open(log_file, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

def main():
    input_data = json.load(sys.stdin)
    transcript_path = input_data.get("transcript_path")
    session_id = input_data.get("session_id", "unknown")

    if not transcript_path:
        return

    ensure_dirs()
    ensure_launchd_installed()

    messages = extract_messages(transcript_path)
    if messages:
        save_log(session_id, messages)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"gangsmem error: {e}", file=sys.stderr)
```

### hooks/inject_memory.py

```python
#!/usr/bin/env python3
"""UserPromptSubmit Hook: 搜索相关记忆并注入"""

import sys
import json
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR / "lib"))

from db import search, db_exists
from tokenizer import tokenize_simple

def main():
    input_data = json.load(sys.stdin)
    prompt = input_data.get("prompt", "")

    if not prompt or not db_exists():
        return

    # 分词
    keywords = tokenize_simple(prompt)
    if not keywords:
        return

    query = " OR ".join(keywords)

    # 搜索
    results = search(query, limit=3)

    if not results:
        return

    # 输出注入内容 (stdout 会被注入到 Claude 上下文)
    print("<related-memories>")
    print("以下是可能相关的历史知识，请自行判断是否有用：")
    print()
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r['title']}")
        print(f"    {r['summary'][:200]}...")
        print()
    print("</related-memories>")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 错误输出到 stderr，不影响 Claude Code
        print(f"gangsmem error: {e}", file=sys.stderr)
```

---

## 开发规范

### 代码风格

- Python 3.10+
- 使用 type hints
- 遵循 PEP 8
- 函数应有 docstring

### 错误处理

- Hook 脚本必须优雅处理错误，不能阻塞 Claude Code
- 使用 stderr 输出错误日志
- 退出码: 0=成功, 非0=失败（但不阻塞）

### 性能要求

- `UserPromptSubmit` hook: < 5 秒
- `SessionEnd` hook: < 30 秒
- FTS5 查询: < 100ms

### 测试

```bash
# 测试 inject_memory
echo '{"prompt": "claude code hooks"}' | python hooks/inject_memory.py

# 测试 session_end
echo '{"transcript_path": "/path/to/test.jsonl"}' | python hooks/session_end.py
```

---

## 使用方式

### 安装

```bash
# 通过 GitHub 安装
/plugin install https://github.com/username/gangsmem

# 本地开发
ln -s /path/to/gangsmem ~/.claude/plugins/gangsmem
```

### Skills

| Skill | 说明 |
|-------|------|
| `/analyze` | 分析未处理的日志，提取知识生成记忆 |
| `/analyze --all` | 重新分析所有日志 |
| `/search <query>` | 深度搜索记忆库 |
| `/rebuild-index` | 重建 FTS5 索引 |
| `/forget <topic>` | 删除指定主题的记忆 |

---

## TODO

### Hooks
- [ ] hooks/session_end.py - 保存对话日志 + 首次自动配置 launchd
- [ ] hooks/inject_memory.py - FTS5 搜索 + 注入记忆

### Scripts (定时任务)
- [ ] scripts/install.py - 安装 launchd 定时任务
- [ ] scripts/uninstall.py - 卸载 launchd 定时任务
- [ ] scripts/scheduled_analyze.py - 定时分析脚本
- [ ] scripts/rebuild_index.py - 重建 FTS5 索引

### Lib
- [ ] lib/db.py - SQLite FTS5 操作
- [ ] lib/tokenizer.py - 分词
- [ ] lib/transcript.py - 解析 transcript

### Skills
- [ ] skills/analyze/SKILL.md - 手动触发分析
- [ ] skills/search/SKILL.md - 深度搜索记忆
- [ ] skills/forget/SKILL.md - 删除记忆

### 其他
- [ ] launchd/com.gangsmem.analyze.plist - 模板文件
- [ ] tests/ - 测试用例
- [ ] README.md - 安装文档
- [ ] .claude-plugin/plugin.json - 插件元数据

---

## 参考资料

- [SQLite FTS5](https://www.sqlite.org/fts5.html)
- [Claude Code Hooks](https://docs.anthropic.com/en/docs/claude-code/hooks)
- [Claude Code Plugins](https://docs.anthropic.com/en/docs/claude-code/plugins)
- [Claude Code Skills](https://docs.anthropic.com/en/docs/claude-code/skills)
