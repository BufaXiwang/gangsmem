# Gangsmem

> Claude Code 智能记忆增强系统

自动记录对话、提取知识、构建索引，并在每次对话时注入相关记忆。

## 特性

- **自动记录** - SessionEnd hook 自动保存对话日志
- **智能分析** - 每天自动分析日志，提取可复用知识
- **全文搜索** - SQLite FTS5 毫秒级搜索
- **自动注入** - 每次对话自动注入相关记忆
- **零配置** - 安装即用，完全自动化

## 安装

```bash
# 通过 GitHub 安装
/plugin install https://github.com/username/gangsmem

# 或本地安装
ln -s /path/to/gangsmem ~/.claude/plugins/gangsmem
```

## 使用

安装后无需任何操作：

1. **对话记录** - 每次 session 结束自动保存
2. **定时分析** - 每天凌晨 3:00 自动分析日志
3. **记忆注入** - 每次提问自动注入相关记忆

### Skills

| Skill | 说明 |
|-------|------|
| `/analyze` | 手动触发分析 |
| `/analyze --all` | 重新分析所有日志 |
| `/search <query>` | 深度搜索记忆 |
| `/forget <topic>` | 删除指定记忆 |

## 数据存储

```
~/.gangsmem/
├── logs/           # 对话日志
├── memory/         # 记忆文档 (Markdown)
├── search.db       # FTS5 搜索索引
├── state.json      # 分析状态
└── config.json     # 配置
```

## 配置

编辑 `~/.gangsmem/config.json`:

```json
{
  "auto_inject": true,
  "max_inject_results": 3,
  "max_inject_chars": 1000,
  "use_jieba": false
}
```

## 卸载

```bash
# 移除定时任务
python3 ~/.claude/plugins/gangsmem/scripts/uninstall.py

# 删除插件
rm -rf ~/.claude/plugins/gangsmem

# 可选：删除数据
rm -rf ~/.gangsmem
```

## 技术栈

- **存储**: 本地文件系统
- **搜索**: SQLite FTS5
- **分析**: Claude CLI
- **调度**: macOS launchd

## License

MIT
