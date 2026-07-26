"""敏感内容检测引擎 — 敏感词匹配 + 上下文合规检查。

用法: echo '<parsed-json>' | python check_sensitive.py
输出: dim-06 维度结果 JSON
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any


# ---------------------------------------------------------------------------
# 敏感词库
# ---------------------------------------------------------------------------

# 领土敏感词（需要上下文检查）
_TERRITORY_TERMS: dict[str, str] = {
    "台湾": "必须为「中国台湾」或「台湾地区」",
    "香港": "必须为「中国香港」",
    "澳门": "必须为「中国澳门」",
    "西藏": "需确认表述规范",
    "新疆": "需确认表述规范",
    "南海": "需确认地图完整",
    "九段线": "需确认地图完整",
    "钓鱼岛": "需确认表述规范",
}

# 绝对违规词（零容忍）
_ABSOLUTE_VIOLATIONS: list[str] = [
    "台湾独立",
    "西藏独立",
    "新疆独立",
    "香港独立",
    "藏独",
    "疆独",
    "台独",
    "港独",
]

# 地图检测关键词
_MAP_KEYWORDS: list[str] = [
    "地图", "map", "领土", "边界", "海岸线", "九段线",
    "南海诸岛", "岛屿", "海域",
]


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

def check_sensitive(paper: dict[str, Any]) -> dict[str, Any]:
    """检查论文敏感内容，返回 dim-06 维度结果。

    Args:
        paper: parse_paper.py 输出的结构化 JSON。

    Returns:
        维度结果 JSON。
    """
    segments = paper.get("segments", [])
    images = paper.get("images", [])

    full_text = "\n".join(seg.get("text", "") for seg in segments)

    findings: list[dict[str, Any]] = []

    # 1. 绝对违规词检查
    for term in _ABSOLUTE_VIOLATIONS:
        if term in full_text:
            findings.append({
                "item": "绝对违规词",
                "actual": f"发现「{term}」",
                "suggestion": "零容忍，必须修改",
            })

    # 2. 领土敏感词上下文检查
    for term, rule in _TERRITORY_TERMS.items():
        occurrences = _find_with_context(full_text, term)
        for ctx in occurrences:
            is_ok = _check_territory_context(term, ctx)
            if not is_ok:
                findings.append({
                    "item": "领土表述",
                    "actual": f"发现「{term}」（上下文: ...{ctx[:80]}...）",
                    "suggestion": rule,
                })

    # 3. 民族宗教歧视检查
    discrimination_terms = ["种族歧视", "民族歧视", "宗教歧视", "性别歧视"]
    for term in discrimination_terms:
        if term in full_text:
            findings.append({
                "item": "歧视内容",
                "actual": f"发现「{term}」相关表述",
                "suggestion": "需人工审核是否存在歧视性语言",
            })

    # 4. 地图图片检查
    map_images = _detect_map_images(images, full_text)
    if map_images:
        findings.append({
            "item": "地图图片",
            "actual": f"检测到 {len(map_images)} 张疑似地图图片",
            "suggestion": "需与天地图标准模板比对，确认地图完整性",
        })

    # 判定
    if any("零容忍" in f.get("suggestion", "") for f in findings):
        status, severity = "failed", "critical"
        interaction_needed = True
    elif len(findings) > 0:
        status, severity = "warning", "major"
        interaction_needed = True
    else:
        status, severity = "passed", "info"
        interaction_needed = False

    return {
        "dimension_id": "06",
        "dimension_name": "敏感内容",
        "status": status,
        "severity": severity,
        "findings": findings,
        "interaction_needed": interaction_needed,
        "detail": f"命中数: {len(findings)}",
    }


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _find_with_context(text: str, term: str, window: int = 40) -> list[str]:
    """查找敏感词并返回上下文。"""
    contexts: list[str] = []
    for match in re.finditer(re.escape(term), text):
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        contexts.append(text[start:end])
    return contexts


def _check_territory_context(term: str, context: str) -> bool:
    """检查领土表述是否符合规范。

    规范:
    - 台湾 → 必须为「中国台湾」或「台湾地区」
    - 香港 → 必须为「中国香港」
    - 澳门 → 必须为「中国澳门」
    """
    if term == "台湾":
        return bool(re.search(r"中国台湾|台湾地区", context))
    elif term == "香港":
        return bool(re.search(r"中国香港", context))
    elif term == "澳门":
        return bool(re.search(r"中国澳门", context))
    # 其他词暂不做上下文判断
    return True


def _detect_map_images(images: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    """检测疑似地图的图片。"""
    map_images: list[dict[str, Any]] = []

    # 检查图片 caption 中是否包含地图关键词
    for img in images:
        caption = img.get("caption", "") or ""
        for kw in _MAP_KEYWORDS:
            if kw.lower() in caption.lower():
                map_images.append(img)
                break

    # 检查文本中是否提及地图
    for kw in _MAP_KEYWORDS:
        if kw.lower() in text.lower():
            # 文本中提到地图，可能存在内嵌地图
            map_images.append({"caption": f"文本提及「{kw}」", "source": "text"})
            break

    return map_images


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            paper = json.load(f)
    else:
        paper = json.load(sys.stdin)

    result = check_sensitive(paper)
    print(json.dumps(result, ensure_ascii=False, indent=2))
