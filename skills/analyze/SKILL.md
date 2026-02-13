---
name: analyze
description: 手动触发分析对话日志，提取知识点生成记忆文档。使用方法：/analyze [--all]
---

## 任务

分析 ~/.gangsmem/logs/ 中的对话日志，提取可复用的知识点。

## 参数

$ARGUMENTS

- 无参数: 只分析未处理的日志
- `--all`: 重新分析所有日志（会重置分析状态）

## 流程

### 第一步：确定待分析的日志

1. 读取 ~/.gangsmem/state.json 获取已分析的 session 列表
2. 如果传入 `--all`，先清空 state.json 中的 analyzed_sessions
3. 找出未分析的日志文件（~/.gangsmem/logs/**/*.jsonl）

### 第二步：读取并分析日志

使用 Read 工具读取日志文件，识别有价值的知识点：
- 解决的问题和方案
- 可泛化的技巧、模式、最佳实践
- 重要的代码片段或命令
- 工具使用方法和配置

### 第三步：检查现有记忆

使用 Glob 工具列出 ~/.gangsmem/memory/*.md 所有现有文档。
对于每个提取的知识点，判断是否与现有文档相关（通过标题、关键词判断）。

### 第四步：更新或创建文档

**情况 A：找到相关文档 → 更新**

1. 使用 Read 读取现有文档
2. 使用 Edit 工具更新文档：
   - 在 frontmatter 的 `sources` 列表中添加新的 session ID
   - 更新 `updated` 日期
   - 在 `keywords` 中添加新的关键词（如果有）
   - 在文档正文中追加新的内容：
     - 使用 "## 补充" 章节
     - 或整合到现有章节
   - 如果新内容与现有内容重复，则整合去重
   - 如果新内容是对现有内容的修正，直接修改原文

**情况 B：没有相关文档 → 创建新文档**

使用 Write 工具创建新文档，格式如下：

```markdown
---
id: document-id-in-english
title: 文档标题
keywords: [关键词1, 关键词2, 关键词3]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [session1, session2]
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

### 第五步：更新状态和索引

1. 更新 ~/.gangsmem/state.json，将已分析的 session ID 添加到 analyzed_sessions
2. 运行 `python3 ~/.claude/plugins/gangsmem/scripts/rebuild_index.py` 重建索引

## 重要原则

- 只提取真正有价值、可复用的知识
- 忽略过于具体或一次性的内容
- **相似主题必须合并到同一文档，避免碎片化**
- 关键词应该是用户可能搜索的词
- 更新文档时保留原有内容的完整性
