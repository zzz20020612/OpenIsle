"""论文分类器

根据论文标题、摘要、关键词等元数据，将论文分类为：
- review: 综述/元分析/概述类论文
- methodology: 方法学/协议/框架类论文
- experimental: 实验性论文（含具体数值和实验动词）
- data_description: 数据描述/案例研究类论文

分类结果用于路由到对应的 Prompt 模板，提升提取质量。
"""
import re
from typing import Dict, Any, Optional


# 分类关键词规则
REVIEW_KEYWORDS = [
    "review", "meta-analysis", "overview", "survey", "systematic review",
    "literature review", "scoping review", "bibliometric",
    "综述", "元分析", "文献回顾", "系统评价",
]

METHODOLOGY_KEYWORDS = [
    "method", "methodology", "protocol", "framework", "approach",
    "algorithm", "technique", "procedure", "design",
    "方法", "协议", "框架", "算法", "技术",
]

EXPERIMENTAL_INDICATORS = [
    # 实验动词
    "experiment", "experimental", "tested", "measured", "analyzed",
    "compared", "evaluated", "validated", "verified",
    "实验", "测试", "测量", "分析", "比较", "评估",
    # 统计术语
    "p-value", "p < 0.05", "significance", "confidence interval",
    "standard deviation", "variance", "regression",
    "p值", "显著性", "置信区间", "标准差", "回归",
]


def classify_paper(paper_metadata: Dict[str, Any]) -> str:
    """对论文进行分类
    
    Args:
        paper_metadata: 论文元数据字典，包含 title, abstract, keywords 等字段
    
    Returns:
        分类结果：'review' | 'methodology' | 'experimental' | 'data_description'
    """
    title = (paper_metadata.get("title") or "").lower()
    abstract = (paper_metadata.get("abstract") or "").lower()
    keywords = (paper_metadata.get("keywords") or "").lower()
    
    # 合并所有文本用于匹配
    all_text = f"{title} {abstract} {keywords}"
    
    # 1. 检查是否为综述类
    review_score = sum(1 for kw in REVIEW_KEYWORDS if kw in all_text)
    if review_score >= 2:  # 至少出现2个综述关键词
        return "review"
    
    # 2. 检查是否为方法学类
    methodology_score = sum(1 for kw in METHODOLOGY_KEYWORDS if kw in all_text)
    if methodology_score >= 2:
        return "methodology"
    
    # 3. 检查是否为实验性论文
    experimental_score = sum(1 for kw in EXPERIMENTAL_INDICATORS if kw in all_text)
    # 检查是否包含具体数值（如 "increased by 15%", "p < 0.05"）
    has_numbers = bool(re.search(r'\d+\.?\d*\s*%|\d+\.\d+|p\s*[<>=]\s*0\.\d+', all_text))
    
    if experimental_score >= 3 and has_numbers:
        return "experimental"
    
    # 4. 默认为数据描述类
    return "data_description"


def get_prompt_template_name(paper_type: str, extraction_type: str) -> str:
    """根据论文类型和提取类型，返回对应的 Prompt 模板名称
    
    Args:
        paper_type: 论文分类结果
        extraction_type: 提取类型 ('knowledge_card' | 'methods' | 'data_points')
    
    Returns:
        Prompt 模板文件名（不含 .txt 后缀）
    """
    # 知识卡片提取
    if extraction_type == "knowledge_card":
        if paper_type == "review":
            return "knowledge_card_review_v1"
        elif paper_type == "methodology":
            return "knowledge_card_method_v1"
        else:  # experimental 和 data_description 使用通用模板
            return "knowledge_card_v1"
    
    # 方法流程提取
    elif extraction_type == "methods":
        if paper_type == "review":
            return "methods_review_v1"
        elif paper_type == "methodology":
            return "methods_methodology_v1"
        elif paper_type == "experimental":
            return "methods_experimental_v1"
        else:
            return "methods_v1"
    
    # 数据点提取（所有类型使用同一模板）
    elif extraction_type == "data_points":
        return "data_points_v1"
    
    # 默认回退
    return "knowledge_card_v1"


def classify_and_get_prompt(paper_metadata: Dict[str, Any], extraction_type: str) -> tuple[str, str]:
    """分类论文并返回对应的 Prompt 模板名称
    
    Args:
        paper_metadata: 论文元数据
        extraction_type: 提取类型
    
    Returns:
        (paper_type, prompt_template_name)
    """
    paper_type = classify_paper(paper_metadata)
    prompt_name = get_prompt_template_name(paper_type, extraction_type)
    return paper_type, prompt_name
