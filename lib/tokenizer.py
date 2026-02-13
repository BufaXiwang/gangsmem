#!/usr/bin/env python3
"""分词工具"""

import re
from typing import List, Set

# 停用词（常见但无意义的词）
STOP_WORDS_EN = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "need",
    "it", "its", "this", "that", "these", "those", "i", "you", "he", "she",
    "we", "they", "what", "which", "who", "whom", "how", "when", "where",
    "why", "if", "then", "else", "so", "as", "not", "no", "yes"
}

STOP_WORDS_ZH = {
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "那", "什么", "怎么", "吗", "呢",
    "啊", "吧", "呀", "嗯", "哦", "哈", "请", "请问", "可以", "能", "想"
}

STOP_WORDS = STOP_WORDS_EN | STOP_WORDS_ZH


def tokenize_simple(text: str) -> List[str]:
    """
    简单分词：英文单词 + 中文片段

    Args:
        text: 输入文本

    Returns:
        分词结果列表（已去重、过滤停用词）
    """
    if not text:
        return []

    tokens: Set[str] = set()

    # 英文单词（至少2个字符）
    english_words = re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{1,}', text.lower())
    tokens.update(english_words)

    # 中文：提取2-4字的连续片段
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    for chars in chinese_chars:
        # 2字组合
        for i in range(len(chars) - 1):
            tokens.add(chars[i:i+2])
        # 3字组合
        for i in range(len(chars) - 2):
            tokens.add(chars[i:i+3])
        # 4字组合
        for i in range(len(chars) - 3):
            tokens.add(chars[i:i+4])

    # 过滤停用词
    tokens = {t for t in tokens if t not in STOP_WORDS}

    return list(tokens)


def tokenize_jieba(text: str) -> List[str]:
    """
    jieba 分词（需安装 jieba）

    Args:
        text: 输入文本

    Returns:
        分词结果列表
    """
    try:
        import jieba
        words = list(jieba.cut(text))
        # 过滤停用词和短词
        words = [w.lower() for w in words if len(w) >= 2 and w not in STOP_WORDS]
        return list(set(words))
    except ImportError:
        return tokenize_simple(text)


def tokenize(text: str, use_jieba: bool = False) -> List[str]:
    """
    分词入口函数

    Args:
        text: 输入文本
        use_jieba: 是否使用 jieba（默认否）

    Returns:
        分词结果列表
    """
    if use_jieba:
        return tokenize_jieba(text)
    return tokenize_simple(text)


def build_fts_query(tokens: List[str], operator: str = "OR") -> str:
    """
    构建 FTS5 查询语句

    Args:
        tokens: 分词列表
        operator: 连接符，"OR" 或 "AND"

    Returns:
        FTS5 查询字符串
    """
    if not tokens:
        return ""

    # 转义特殊字符
    escaped = []
    for t in tokens:
        # FTS5 特殊字符需要用双引号包裹
        if any(c in t for c in ['"', '*', '-', '+', '(', ')', ':']):
            escaped.append(f'"{t}"')
        else:
            escaped.append(t)

    return f" {operator} ".join(escaped)
