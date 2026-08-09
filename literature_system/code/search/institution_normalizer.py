"""机构名归一化工具。

在作者提取/填充阶段即对机构名进行清洗，避免后续机构合作网络出现
大量因大小写、缩写、拼写差异导致的重复节点。
"""
from __future__ import annotations

import re
from typing import List


# 常见缩写扩展（按优先级排序，较长的模式优先）
_ABBREVIATION_MAP = {
    r"\buniv\b\.?": "university",
    r"\bcol\b\.?": "college",
    r"\binst\b\.?": "institute",
    r"\btech\b\.?": "technology",
    r"\bsci\b\.?": "science",
    r"\beng\b\.?": "engineering",
    r"\bdept\b\.?": "department",
    r"\blab\b\.?": "laboratory",
    r"\bhosp\b\.?": "hospital",
    r"\bacad\b\.?": "academy",
    r"\bassoc\b\.?": "association",
    r"\bfound\b\.?": "foundation",
    r"\bcorp\b\.?": "corporation",
    r"\binc\b\.?": "incorporated",
    r"\bltd\b\.?": "limited",
    r"\bagr\b\.?": "agricultural",
    r"\bres\b\.?": "research",
    r"\bcent\b\.?": "center",
    r"\bcntr\b\.?": "center",
    r"\bsch\b\.?": "school",
    r"\bfac\b\.?": "faculty",
    r"\bdiv\b\.?": "division",
    r"\bprog\b\.?": "program",
    r"\bnatl\b\.?": "national",
    r"\bintl\b\.?": "international",
    r"\bmgmt\b\.?": "management",
    r"\benv\b\.?": "environment",
    r"\bdev\b\.?": "development",
    r"\bsust\b\.?": "sustainable",
}


def _remove_punctuation_noise(name: str) -> str:
    """去除末尾标点与多余分隔符，并去掉开头的定冠词。"""
    name = re.sub(r"[,;]+$", "", name)
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"^(the|la|le|el|los|las)\s+", "", name, flags=re.IGNORECASE)
    return name.strip()


def _expand_abbreviations(name: str) -> str:
    """展开常见机构缩写。"""
    # 先整体替换一些高频复合缩写
    name = re.sub(r"\buniv\b\.?\s*of\b", "university of", name, flags=re.IGNORECASE)
    name = re.sub(r"\btech\b\.?\s*univ\b\.?", "technology university", name, flags=re.IGNORECASE)

    for pattern, replacement in _ABBREVIATION_MAP.items():
        name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)
    # 统一 programme / program 拼写差异
    name = re.sub(r"\bprogramme\b", "program", name, flags=re.IGNORECASE)
    return name


# 需要保持全大写的常见机构缩写/首字母缩略词
_FORCE_UPPER_WORDS = {
    "eth", "csi", "csiro", "mit", "ucla", "cnrs", "inra", "inrae",
    "cnr", "cea", "cern", "nasa", "who", "un", "eu", "fao", "oecd",
    "imperial", "cirad", "ird", "jrc", "abc", "rmit", "epfl", "ethz",
}


def _title_case(name: str) -> str:
    """将小写机构名转为标题式大小写，保留常见小词，并保护特定缩写全大写。"""
    minor_words = {"of", "and", "for", "the", "in", "on", "at", "to", "a", "an", "de", "et", "la", "le"}
    words = name.split()
    if not words:
        return name
    result = []
    for i, w in enumerate(words):
        low = w.lower()
        if low in _FORCE_UPPER_WORDS:
            result.append(low.upper())
        elif i == 0 or low not in minor_words:
            result.append(w.capitalize())
        else:
            result.append(w.lower())
    return " ".join(result)


def normalize_institution_name(name: str) -> str:
    """归一化单个机构名。

    流程：去空格 -> 小写 -> 展开缩写 -> 去标点噪声 -> 标题化。
    """
    if not name or not str(name).strip():
        return ""
    name = str(name).strip()
    name = name.lower()
    name = _expand_abbreviations(name)
    name = _remove_punctuation_noise(name)
    name = _title_case(name)
    return name


def normalize_affiliations(names: List[str]) -> List[str]:
    """归一化机构名列表并去重（保留顺序）。"""
    seen = set()
    result = []
    for n in names:
        normalized = normalize_institution_name(n)
        if normalized and normalized.lower() not in seen:
            seen.add(normalized.lower())
            result.append(normalized)
    return result
