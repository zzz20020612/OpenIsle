"""指标名归一化与数值解析模块

功能：
1. 将不同论文中的相似指标名归一化为标准形式（如 cattle / cattle density / cattle count → cattle）
2. 解析 metric_value 字段，支持范围、不等式、文本等多种格式
3. 提供数值提取和归一化工具函数

设计原则：
- 归一化规则基于领域词典 + 规则匹配
- 数值解析支持多种格式（单一数值、范围、不等式、文本）
- 保留原始文本用于审计和回溯
"""
import re
from typing import Optional, Tuple, Dict, List


# 畜牧业/农业常用指标词表（用于归一化）
METRIC_SYNONYMS = {
    # 产量相关
    "yield": ["yield", "productivity", "output", "production"],
    "biomass": ["biomass", "biomass yield", "biomass production"],
    
    # 密度/数量相关
    "density": ["density", "concentration", "abundance"],
    "count": ["count", "number", "quantity"],
    "cattle": ["cattle", "cattle density", "cattle count", "cattle number"],
    "sheep": ["sheep", "sheep density", "sheep count"],
    "goat": ["goat", "goats", "sheep and goats", "sheep+goats"],
    
    # 排放相关
    "emission": ["emission", "emissions", "ghg", "greenhouse gas", "co2", "ch4", "methane"],
    "carbon": ["carbon", "c", "carbon footprint"],
    
    # 效率相关
    "efficiency": ["efficiency", "conversion rate", "utilization"],
    "reduction": ["reduction", "decrease", "mitigation"],
    
    # 环境指标
    "temperature": ["temperature", "temp"],
    "moisture": ["moisture", "humidity", "water content"],
    "ph": ["ph", "acidity"],
    
    # 多样性指标
    "diversity": ["diversity", "diversity index", "shannon", "simpson"],
    "richness": ["richness", "species richness"],
    "evenness": ["evenness", "species evenness"],
}

# 停用词（归一化时去除）
STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "at", "for", "to", "with",
    "by", "from", "and", "or", "per", "vs", "versus",
}


def normalize_metric_name(metric_name: str) -> str:
    """归一化指标名
    
    Args:
        metric_name: 原始指标名（如 "cattle density", "Cattle Density"）
    
    Returns:
        归一化后的指标名（如 "cattle"）
    
    Examples:
        >>> normalize_metric_name("cattle density")
        'cattle'
        >>> normalize_metric_name("Cattle Count")
        'cattle'
        >>> normalize_metric_name("sheep and goats")
        'goat'
    """
    if not metric_name:
        return ""
    
    # 转小写
    normalized = metric_name.lower().strip()
    
    # 去除特殊符号（如 + → and）
    normalized = normalized.replace("+", " and ")
    
    # 去除停用词
    words = normalized.split()
    words = [w for w in words if w not in STOPWORDS]
    normalized = " ".join(words)
    
    # 单复数统一（简单规则：去除末尾 s）
    if normalized.endswith("ies"):
        normalized = normalized[:-3] + "y"
    elif normalized.endswith("es") and len(normalized) > 3:
        normalized = normalized[:-2]
    elif normalized.endswith("s") and not normalized.endswith("ss"):
        normalized = normalized[:-1]
    
    # 查找同义词映射
    for canonical, synonyms in METRIC_SYNONYMS.items():
        if normalized in synonyms or normalized == canonical:
            return canonical
        # 部分匹配（如 "cattle density" → "cattle"）
        for synonym in synonyms:
            if synonym in normalized or normalized in synonym:
                return canonical
    
    # 未匹配到同义词，返回清理后的原始名称
    return normalized


def parse_metric_value(value) -> Tuple[Optional[float], Optional[str]]:
    """解析 metric_value 字段，支持多种格式
    
    Args:
        value: 原始数值（可以是数字、字符串、None）
    
    Returns:
        (numeric_value, original_text)
        - numeric_value: 可解析为单一数值时返回 float，否则返回 None
        - original_text: 原始文本（用于审计和回溯）
    
    Examples:
        >>> parse_metric_value(123.45)
        (123.45, None)
        >>> parse_metric_value("123.45")
        (123.45, None)
        >>> parse_metric_value("50 to 150")
        (50.0, "50 to 150")
        >>> parse_metric_value(">100")
        (100.0, ">100")
        >>> parse_metric_value("high")
        (None, "high")
    """
    if value is None:
        return None, None
    
    # 已经是数字
    if isinstance(value, (int, float)):
        return float(value), None
    
    # 转为字符串
    value_str = str(value).strip()
    if not value_str:
        return None, None
    
    # 尝试直接解析为数字
    try:
        return float(value_str), None
    except ValueError:
        pass
    
    # 尝试解析范围（如 "50 to 150", "50-150"）
    range_match = re.match(
        r"([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*(?:to|-|~)\s*([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)",
        value_str,
        re.IGNORECASE
    )
    if range_match:
        # 取范围的第一个值作为 numeric_value
        try:
            numeric = float(range_match.group(1))
            return numeric, value_str
        except ValueError:
            pass
    
    # 尝试解析不等式（如 ">100", "<50", ">=100"）
    inequality_match = re.match(
        r"([<>]=?)\s*([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)",
        value_str,
        re.IGNORECASE
    )
    if inequality_match:
        try:
            numeric = float(inequality_match.group(2))
            return numeric, value_str
        except ValueError:
            pass
    
    # 尝试提取第一个数字（如 "approximately 100 kg"）
    number_match = re.search(r"([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)", value_str)
    if number_match:
        try:
            numeric = float(number_match.group(1))
            return numeric, value_str
        except ValueError:
            pass
    
    # 无法解析为数值，保留原始文本
    return None, value_str


def normalize_existing_metrics(db_path: str = None):
    """回填历史数据的 metric_name_normalized 字段
    
    Args:
        db_path: 数据库路径（默认使用 config.SQLITE_PATH）
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    
    import config
    from db import get_connection
    
    if db_path:
        config.SQLITE_PATH = Path(db_path)
    
    conn = get_connection(init_schema=False, row_factory=True)
    
    # 查询所有未归一化的记录
    cur = conn.cursor()
    cur.execute(
        "SELECT id, metric_name FROM paper_data_points "
        "WHERE metric_name_normalized IS NULL OR metric_name_normalized = ''"
    )
    rows = cur.fetchall()
    
    updated = 0
    for row in rows:
        metric_name = row["metric_name"]
        normalized = normalize_metric_name(metric_name)
        
        conn.execute(
            "UPDATE paper_data_points SET metric_name_normalized = ? WHERE id = ?",
            (normalized, row["id"])
        )
        updated += 1
    
    conn.commit()
    conn.close()
    
    print(f"已归一化 {updated} 条记录的 metric_name_normalized 字段")


if __name__ == "__main__":
    # 测试归一化
    test_cases = [
        "cattle",
        "cattle density",
        "Cattle Count",
        "sheep and goats",
        "sheep+goats",
        "biomass yield",
        "ghg emission",
        "temperature",
    ]
    
    print("指标名归一化测试:")
    for tc in test_cases:
        print(f"  {tc:20s} → {normalize_metric_name(tc)}")
    
    print("\n数值解析测试:")
    value_cases = [
        123.45,
        "123.45",
        "50 to 150",
        ">100",
        "<50",
        "approximately 100 kg",
        "high",
        "N/A",
    ]
    for vc in value_cases:
        numeric, original = parse_metric_value(vc)
        print(f"  {str(vc):20s} → numeric={numeric}, original={original}")
