#!/usr/bin/env python3
"""
重建 FTS5 搜索索引

扫描 memory/*.md 文件，解析 frontmatter，构建全文索引
"""

import sys
import re
from pathlib import Path
from datetime import datetime

PLUGIN_DIR = Path(__file__).parent.parent
GANGSMEM_DIR = Path.home() / ".gangsmem"
MEMORY_DIR = GANGSMEM_DIR / "memory"

# 添加 lib 到 path
sys.path.insert(0, str(PLUGIN_DIR / "lib"))


def log(msg: str):
    """输出日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


def parse_frontmatter(content: str) -> tuple:
    """
    解析 markdown frontmatter

    Returns:
        (frontmatter_dict, body_content)
    """
    # 匹配 YAML frontmatter
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        return {}, content

    yaml_content = match.group(1)
    body = match.group(2)

    # 简单解析 YAML（不依赖 pyyaml）
    frontmatter = {}
    for line in yaml_content.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            # 处理列表
            if value.startswith('[') and value.endswith(']'):
                # [item1, item2, item3]
                items = value[1:-1].split(',')
                value = [item.strip().strip('"\'') for item in items if item.strip()]
            else:
                # 去除引号
                value = value.strip('"\'')

            frontmatter[key] = value

    return frontmatter, body


def extract_summary(content: str, max_length: int = 200) -> str:
    """提取摘要（跳过标题和空行）"""
    lines = []
    for line in content.split('\n'):
        line = line.strip()
        # 跳过标题、空行、代码块标记
        if not line or line.startswith('#') or line.startswith('```'):
            continue
        lines.append(line)
        if sum(len(l) for l in lines) >= max_length:
            break

    summary = ' '.join(lines)
    if len(summary) > max_length:
        summary = summary[:max_length] + "..."
    return summary


def rebuild_index() -> int:
    """重建索引，返回索引的文档数量"""
    from db import init_db, clear_all, index_document

    # 初始化数据库
    init_db()

    # 清空现有索引
    clear_all()

    if not MEMORY_DIR.exists():
        log("Memory directory does not exist")
        return 0

    # 扫描所有 markdown 文件
    md_files = list(MEMORY_DIR.glob("*.md"))
    log(f"Found {len(md_files)} memory files")

    indexed = 0
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)

            doc_id = frontmatter.get("id", md_file.stem)
            title = frontmatter.get("title", md_file.stem)
            keywords = frontmatter.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [keywords]

            summary = extract_summary(body)

            doc = {
                "id": doc_id,
                "title": title,
                "keywords": keywords,
                "content": body,
                "summary": summary
            }

            if index_document(doc):
                indexed += 1
                log(f"  Indexed: {title}")
            else:
                log(f"  Failed: {title}")

        except Exception as e:
            log(f"  Error processing {md_file.name}: {e}")

    log(f"Indexed {indexed} documents")
    return indexed


def main():
    log("Rebuilding FTS5 index...")
    count = rebuild_index()
    log(f"Done. Total: {count} documents")


if __name__ == "__main__":
    main()
