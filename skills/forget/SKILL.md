---
name: forget
description: 删除指定的记忆文档。使用方法：/forget <topic or filename>
---

## 任务

从记忆库中删除指定的文档。

## 要删除的内容

$ARGUMENTS

## 步骤

1. 列出 ~/.gangsmem/memory/*.md 文件
2. 根据参数查找匹配的文档（支持文件名或关键词匹配）
3. 显示将要删除的文档，请求用户确认
4. 确认后删除文件
5. 运行 `python3 ~/.claude/plugins/gangsmem/scripts/rebuild_index.py` 重建索引

## 注意

- 删除前必须确认
- 支持模糊匹配
- 删除后会自动重建索引
