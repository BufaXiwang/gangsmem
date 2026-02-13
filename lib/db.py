#!/usr/bin/env python3
"""SQLite FTS5 数据库操作"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional

GANGSMEM_DIR = Path.home() / ".gangsmem"
DB_PATH = GANGSMEM_DIR / "search.db"


def db_exists() -> bool:
    """检查数据库是否存在"""
    return DB_PATH.exists()


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    GANGSMEM_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> sqlite3.Connection:
    """初始化 FTS5 数据库"""
    conn = get_connection()
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories USING fts5(
            id,
            title,
            keywords,
            content,
            summary,
            tokenize='porter unicode61'
        )
    """)
    conn.commit()
    return conn


def search(query: str, limit: int = 5) -> List[Dict]:
    """
    全文搜索记忆文档

    Args:
        query: 搜索词（支持 FTS5 语法，如 "word1 OR word2"）
        limit: 返回结果数量限制

    Returns:
        匹配的文档列表，包含 id, title, summary, score
    """
    if not db_exists():
        return []

    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT id, title, summary, bm25(memories) as score
            FROM memories
            WHERE memories MATCH ?
            ORDER BY score
            LIMIT ?
        """, (query, limit))

        results = []
        for row in cursor:
            results.append({
                "id": row["id"],
                "title": row["title"],
                "summary": row["summary"],
                "score": row["score"]
            })
        return results
    except sqlite3.OperationalError:
        # 查询语法错误等
        return []
    finally:
        conn.close()


def index_document(doc: Dict) -> bool:
    """
    索引单个文档

    Args:
        doc: 包含 id, title, keywords, content, summary 的字典

    Returns:
        是否成功
    """
    conn = get_connection()
    try:
        # 先删除旧的（如果存在）
        conn.execute("DELETE FROM memories WHERE id = ?", (doc["id"],))

        # 插入新的
        keywords_str = " ".join(doc.get("keywords", []))
        conn.execute("""
            INSERT INTO memories(id, title, keywords, content, summary)
            VALUES (?, ?, ?, ?, ?)
        """, (
            doc["id"],
            doc["title"],
            keywords_str,
            doc["content"],
            doc["summary"]
        ))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def delete_document(doc_id: str) -> bool:
    """删除文档"""
    if not db_exists():
        return False

    conn = get_connection()
    try:
        conn.execute("DELETE FROM memories WHERE id = ?", (doc_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def clear_all() -> bool:
    """清空所有索引"""
    if not db_exists():
        return True

    conn = get_connection()
    try:
        conn.execute("DELETE FROM memories")
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_all_ids() -> List[str]:
    """获取所有已索引的文档 ID"""
    if not db_exists():
        return []

    conn = get_connection()
    try:
        cursor = conn.execute("SELECT id FROM memories")
        return [row["id"] for row in cursor]
    finally:
        conn.close()
