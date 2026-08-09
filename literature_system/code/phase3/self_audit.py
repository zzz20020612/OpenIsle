"""知识卡片质量校验（5 项 self-audit）。

借鉴 paper-evidence-distiller 的 self-audit 设计：
1. 信息完整性：遗漏会改变结论解释的主张
2. 重复/填充：同一发现是否在两章节重复 / 空话填充
3. 回链：用锚点 30 秒内能定位原文位置（验证 section_id/figure_id 是否存在）
4. 用词边界：是否把"相关"写成"导致"
5. 作者 vs 我们：作者已证明的 vs 当前研究启发是否混淆
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from db import get_connection
from logger import get_logger

logger = get_logger("phase3.self_audit")

# 诚实 hedge 检查：因果性词汇列表
CAUSAL_WORDS = ["导致", "证明", "确定", "引起", "造成", "使得", "caused", "proved", "demonstrated"]
ASSOCIATION_WORDS = ["相关", "关联", "暗示", "推测", "作者推测", "associated", "correlated", "suggested", "hypothesized"]

# 空话填充词汇
FILLER_WORDS = ["本文很重要", "本研究具有重要意义", "具有重要意义", "做出了贡献", "this paper is important"]


def run_audit(paper_id: int) -> Dict[str, Any]:
    """对单篇论文的知识卡片执行 5 项质量校验。

    Args:
        paper_id: 论文 ID

    Returns:
        {
            "paper_id": int,
            "quality_score": float,  # 0.0-1.0
            "checks": {
                "completeness": {"passed": bool, "issues": [...]},
                "no_duplicate": {"passed": bool, "issues": [...]},
                "anchor_valid": {"passed": bool, "issues": [...]},
                "hedge_honesty": {"passed": bool, "issues": [...]},
                "author_vs_user": {"passed": bool, "issues": [...]},
            }
        }
    """
    from .extractor import _get_existing_card

    card = _get_existing_card(paper_id)
    if not card:
        return {
            "paper_id": paper_id,
            "quality_score": 0.0,
            "checks": {},
            "error": "知识卡片不存在",
        }

    checks = {}
    checks["completeness"] = _check_completeness(card)
    checks["no_duplicate"] = _check_no_duplicate(card)
    checks["anchor_valid"] = _check_anchor_valid(paper_id, card)
    checks["hedge_honesty"] = _check_hedge_honesty(card)
    checks["author_vs_user"] = _check_author_vs_user(card)

    # 计算总分（增强版：基于规则评分 + issues 扣分）
    quality_score = evaluate_quality_score(card, audit_report={"checks": checks})

    # 更新数据库中的 quality_score 和 audit_report
    _save_audit_result(paper_id, quality_score, checks)

    return {
        "paper_id": paper_id,
        "quality_score": quality_score,
        "checks": checks,
    }


def evaluate_quality_score(card: Dict[str, Any], audit_report: Optional[Dict[str, Any]] = None) -> float:
    """增强版 quality_score 评分器（满分 1.0，分布更分散）。

    设计目标（2026-08-01 校准）：
    - 避免分数集中 0.8-1.0：原版本 5 项各 0.2，绝大多数卡都满分。
    - 提高「具体数值 / 统计显著性」的权重（10% → 25%）。
    - 按 audit_report 中的 issues 严重程度扣分：
        * warning -0.03、error -0.08（更平缓，保留区分度）。
    - 拆分 key_claims 数量与质量两个维度：
        * 数量 3-5 条 +0.05
        * 每条 claim 质量（claim+evidence+anchor+数值） +0.15

    计分明细（满分 1.0）：
        1. 核心字段完整        +0.10（core_answer 长度 >30 + evidence_generation 非空）
        2. boundaries 三桶     +0.10（author_acknowledged/result_shown/unconfirmed 都非空）
        3. reusable_inspiration +0.05（非空列表）
        4. key_claims 数量 3-5  +0.05
        5. key_claims 质量      +0.20（所有 claim 含 claim/evidence/anchor+数值）
        6. anchor 有效性        +0.10（无失效 section_id/figure_id）
        7. hedge 边界           +0.10（无 hedge 升级 + 因果词有 condition）
        8. author vs user       +0.10（无作者/我们混淆）
        9. issues 扣分          最多 -0.20（warning -0.03, error -0.08 累加）

    Args:
        card: 知识卡片字典
        audit_report: run_audit() 返回的 checks 字典（用于 issues 扣分）

    Returns:
        quality_score (0.0-1.0)
    """
    score = 0.0
    score_max = 0.0  # 累计上限，便于归一化

    # 1. 核心字段完整（0.10）
    score_max += 0.10
    core_answer = card.get("core_answer", "")
    evidence_generation = card.get("evidence_generation", "")
    if core_answer and len(core_answer) > 30 and evidence_generation:
        score += 0.10

    # 2. boundaries 三桶（0.10）
    score_max += 0.10
    boundaries = card.get("boundaries", {})
    if isinstance(boundaries, dict):
        buckets = [
            boundaries.get("author_acknowledged"),
            boundaries.get("result_shown"),
            boundaries.get("unconfirmed"),
        ]
        non_empty = sum(1 for b in buckets if b)
        if non_empty == 3:
            score += 0.10
        elif non_empty == 2:
            score += 0.05

    # 3. reusable_inspiration 非空（0.05）
    score_max += 0.05
    reusable_inspiration = card.get("reusable_inspiration", [])
    if isinstance(reusable_inspiration, list) and len(reusable_inspiration) >= 1:
        score += 0.05

    # 4. key_claims 数量（0.05）
    score_max += 0.05
    claims = card.get("key_claims", [])
    if isinstance(claims, list) and 3 <= len(claims) <= 5:
        score += 0.05

    # 5. key_claims 质量（0.20）
    score_max += 0.20
    if isinstance(claims, list) and claims:
        valid_claims = 0
        numeric_claims = 0
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            has_claim = bool(claim.get("claim"))
            has_evidence = bool(claim.get("evidence"))
            has_anchor = bool(claim.get("anchor"))
            if has_claim and has_evidence and has_anchor:
                valid_claims += 1
            if _claim_has_numeric(claim.get("claim", ""), claim.get("evidence", "")):
                numeric_claims += 1

        # 全部 claim 结构完整 + 0.10
        if valid_claims == len(claims):
            score += 0.10
        # 至少 50% 含具体数值 + 0.10
        if numeric_claims >= max(1, len(claims) * 0.5):
            score += 0.10
        elif numeric_claims >= 1:
            score += 0.05

    # 6-8. issues 扣分：基于 audit_report 校验
    if audit_report and isinstance(audit_report, dict):
        checks = audit_report.get("checks", {})
        if isinstance(checks, dict):
            # 6. anchor 有效性（0.10）
            score_max += 0.10
            anchor_check = checks.get("anchor_valid", {})
            if anchor_check.get("passed"):
                score += 0.10

            # 7. hedge 边界（0.10）
            score_max += 0.10
            hedge_check = checks.get("hedge_honesty", {})
            if hedge_check.get("passed"):
                score += 0.10

            # 8. author vs user（0.10）
            score_max += 0.10
            author_check = checks.get("author_vs_user", {})
            if author_check.get("passed"):
                score += 0.10

            # 9. issues 扣分（最多 -0.20）
            # 通过 issue 文案粗略区分严重程度：
            # - "可能存在 hedge 升级" / "误将作者发现" / "应移入 reusable_inspiration" → error
            # - 其他（如 "缺少具体数值"、"anchor 无效"）→ warning
            penalty = 0.0
            error_keywords = ["可能存在 hedge 升级", "误将作者发现", "应移入 reusable_inspiration", "hedge"]
            for cname, cdata in checks.items():
                if not isinstance(cdata, dict):
                    continue
                issues = cdata.get("issues", []) or []
                for issue in issues:
                    if not isinstance(issue, str):
                        continue
                    if any(kw in issue for kw in error_keywords):
                        penalty += 0.03
                    else:
                        penalty += 0.01
            penalty = min(penalty, 0.20)
            score = max(0.0, score - penalty)

    # 归一化到 0-1 范围（保留两位小数）
    if score_max > 0:
        score = min(score / score_max, 1.0)
    return round(score, 2)


def validate_key_claims(key_claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    """校验 key_claims 质量，识别需要精炼的 claims。
    
    检查项：
    1. 是否包含具体数值（p 值、置信区间、效应量等）
    2. evidence 是否充分（长度 > 20 且包含统计术语）
    3. anchor 是否有效（section_id 或 figure_id 非空）
    
    Args:
        key_claims: key_claims 列表
    
    Returns:
        {
            "needs_refinement": bool,  # 是否需要精炼
            "issues": [
                {"claim_index": int, "issue_type": str, "message": str}
            ]
        }
    """
    issues = []
    
    if not isinstance(key_claims, list) or not key_claims:
        return {"needs_refinement": False, "issues": []}
    
    for i, claim in enumerate(key_claims):
        if not isinstance(claim, dict):
            continue
        
        claim_text = claim.get("claim", "")
        evidence_text = claim.get("evidence", "")
        anchor = claim.get("anchor", {})
        
        # 检查 1：是否包含具体数值
        if not _claim_has_numeric(claim_text, evidence_text):
            issues.append({
                "claim_index": i,
                "issue_type": "no_numeric",
                "message": f"key_claims[{i}] 缺少具体数值（p 值、置信区间、效应量等）"
            })
        
        # 检查 2：evidence 是否充分
        if not evidence_text or len(evidence_text) < 20:
            issues.append({
                "claim_index": i,
                "issue_type": "insufficient_evidence",
                "message": f"key_claims[{i}] 证据描述过短（<20 字符）"
            })
        elif not _evidence_has_statistical_term(evidence_text):
            issues.append({
                "claim_index": i,
                "issue_type": "no_statistical_term",
                "message": f"key_claims[{i}] 证据中缺少统计术语（p 值、CI、效应量等）"
            })
        
        # 检查 3：anchor 是否有效
        if not anchor or not isinstance(anchor, dict):
            issues.append({
                "claim_index": i,
                "issue_type": "no_anchor",
                "message": f"key_claims[{i}] 缺少 anchor"
            })
        elif not anchor.get("section_id") and not anchor.get("figure_id"):
            issues.append({
                "claim_index": i,
                "issue_type": "invalid_anchor",
                "message": f"key_claims[{i}] anchor 无效（section_id 和 figure_id 都为空）"
            })
    
    # 判断是否需要精炼：有任何 issue 就需要精炼
    needs_refinement = len(issues) > 0
    
    return {
        "needs_refinement": needs_refinement,
        "issues": issues
    }


def _claim_has_numeric(claim_text: str, evidence_text: str) -> bool:
    """检查 claim 或 evidence 中是否包含具体数值。
    
    检查模式：
    - p 值：p < 0.05, p = 0.001, p < 0.001
    - 置信区间：95% CI, CI: 1.2-3.4
    - 百分比：15%, 23.5%
    - 效应量：Cohen's d = 0.5, OR = 2.3, RR = 1.5
    - 样本量：N = 100, n = 50
    """
    combined_text = f"{claim_text} {evidence_text}".lower()
    
    # p 值模式
    if re.search(r'p\s*[<>=]\s*0\.\d+', combined_text):
        return True
    
    # 置信区间模式
    if re.search(r'(95%\s*)?ci[:\s]', combined_text):
        return True
    
    # 百分比模式
    if re.search(r'\d+\.?\d*\s*%', combined_text):
        return True
    
    # 效应量模式
    if re.search(r"(cohen'?s?\s*d|odds\s*ratio|relative\s*risk|hazard\s*ratio|orr?\b|rr\b|hr\b)\s*[=:]\s*\d+", combined_text):
        return True
    
    # 样本量模式
    if re.search(r'[Nn]\s*[=:]\s*\d+', combined_text):
        return True
    
    # 一般数值模式（至少包含一个数字）
    if re.search(r'\d+\.?\d*', combined_text):
        # 但要排除纯年份（如 2020, 2021, 2020年, 2021年）
        # 匹配年份模式：19xx 或 20xx，后面可能跟"年"
        years = re.findall(r'(?:19|20)\d{2}(?:年)?', combined_text)
        numbers = re.findall(r'\d+\.?\d*', combined_text)
        # 如果数字数量大于年份数量，说明有其他数值
        if len(numbers) > len(years):
            return True
    
    return False


def _evidence_has_statistical_term(evidence_text: str) -> bool:
    """检查 evidence 中是否包含统计学术语或模式。"""
    text = evidence_text.lower()
    
    # 统计学术语列表（不包含"显著"，因为需要与数值结合）
    statistical_terms = [
        'p value', 'p-value', 'p值',
        'confidence interval', 'ci', '置信区间',
        'standard deviation', 'sd', '标准差',
        'standard error', 'se', '标准误',
        'effect size', '效应量',
        'cohen', 'odds ratio', 'relative risk', 'hazard ratio',
        'regression', '回归',
        'significance',
        'sample size', '样本量',
        'meta-analysis', '元分析',
        'heterogeneity', '异质性',
    ]
    
    # 检查术语
    if any(term in text for term in statistical_terms):
        return True
    
    # 检查统计模式（正则表达式）
    # p 值模式：p < 0.05, p = 0.001, p > 0.05
    if re.search(r'p\s*[<>=]\s*0\.\d+', text):
        return True
    
    # 置信区间模式：95% CI, CI: 1.2-3.4
    if re.search(r'(95%\s*)?ci[:\s]', text):
        return True
    
    # 百分比模式：15%, 23.5%
    if re.search(r'\d+\.?\d*\s*%', text):
        return True
    
    # 效应量模式：Cohen's d = 0.5, OR = 2.3, RR = 1.5
    if re.search(r"(cohen'?s?\s*d|odds\s*ratio|relative\s*risk|hazard\s*ratio|orr?\b|rr\b|hr\b)\s*[=:]\s*\d+", text):
        return True
    
    # 样本量模式：N = 100, n = 50
    if re.search(r'[Nn]\s*[=:]\s*\d+', text):
        return True
    
    # "显著"需要与数值结合才算统计术语
    if '显著' in text and re.search(r'\d+\.?\d*', text):
        return True
    
    return False


def _check_completeness(card: Dict) -> Dict[str, Any]:
    """1. 信息完整性检查。"""
    issues = []

    # 检查关键字段是否存在
    if not card.get("research_question"):
        issues.append("research_question 为空")
    if not card.get("core_answer"):
        issues.append("core_answer 为空")
    if not card.get("evidence_generation"):
        issues.append("evidence_generation 为空")

    # 检查 key_claims 数量（3-5 条为佳）
    claims = card.get("key_claims", [])
    if not isinstance(claims, list):
        issues.append("key_claims 不是列表")
    elif len(claims) == 0:
        issues.append("key_claims 为空")
    elif len(claims) > 7:
        issues.append(f"key_claims 过多（{len(claims)} 条，建议 3-5 条）")

    # 检查 boundaries 三桶
    boundaries = card.get("boundaries", {})
    if isinstance(boundaries, dict):
        for bucket in ["author_acknowledged", "result_shown", "unconfirmed"]:
            if not boundaries.get(bucket):
                issues.append(f"boundaries.{bucket} 为空（建议至少填写'无'或'原文未报告'）")

    # 检查 reusable_inspiration
    if not card.get("reusable_inspiration"):
        issues.append("reusable_inspiration 为空")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


def _check_no_duplicate(card: Dict) -> Dict[str, Any]:
    """2. 重复/填充检查。"""
    issues = []

    # 检查 key_claims 之间是否有重复
    claims = card.get("key_claims", [])
    if isinstance(claims, list):
        claim_texts = [c.get("claim", "") for c in claims if isinstance(c, dict)]
        for i, t1 in enumerate(claim_texts):
            for j, t2 in enumerate(claim_texts[i + 1 :], i + 1):
                if _text_similarity(t1, t2) > 0.8:
                    issues.append(f"key_claims[{i}] 与 [{j}] 相似度过高（>80%）")

    # 检查 core_answer 与 abstract 重复（这里只能检查 core_answer 自身）
    core_answer = card.get("core_answer", "")
    for filler in FILLER_WORDS:
        if filler in core_answer:
            issues.append(f"core_answer 包含空话填充: '{filler}'")

    # 检查 research_question 是否在 core_answer 中重复
    rq = card.get("research_question", "")
    if rq and core_answer and rq in core_answer:
        issues.append("research_question 在 core_answer 中重复出现")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


def _check_anchor_valid(paper_id: int, card: Dict) -> Dict[str, Any]:
    """3. 回链检查（验证 section_id / figure_id 是否存在）。"""
    issues = []

    # 收集数据库中真实的 section_id 和 figure_id
    valid_section_ids = set()
    valid_figure_ids = set()

    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM paper_sections WHERE paper_id=?", (paper_id,))
        valid_section_ids = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT id FROM paper_figures WHERE paper_id=?", (paper_id,))
        valid_figure_ids = {r[0] for r in cur.fetchall()}
    finally:
        conn.close()

    # 检查每个 key_claim 的 anchor
    claims = card.get("key_claims", [])
    if isinstance(claims, list):
        for i, claim in enumerate(claims):
            if not isinstance(claim, dict):
                continue
            anchor = claim.get("anchor", {})
            if not isinstance(anchor, dict):
                issues.append(f"key_claims[{i}].anchor 不是字典")
                continue

            section_id = anchor.get("section_id")
            figure_id = anchor.get("figure_id")

            # 至少有一个锚点
            if section_id is None and figure_id is None:
                issues.append(f"key_claims[{i}] 无锚点（section_id 和 figure_id 都为 null）")
                continue

            # 验证锚点存在
            if section_id is not None and section_id not in valid_section_ids:
                issues.append(
                    f"key_claims[{i}].anchor.section_id={section_id} 不存在于 paper_sections"
                )
            if figure_id is not None and figure_id not in valid_figure_ids:
                issues.append(
                    f"key_claims[{i}].anchor.figure_id={figure_id} 不存在于 paper_figures"
                )

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


def _check_hedge_honesty(card: Dict) -> Dict[str, Any]:
    """4. 用词边界检查（"相关"不得升级为"导致"）。"""
    issues = []

    # 检查 key_claims 中是否误用因果性词汇
    claims = card.get("key_claims", [])
    if isinstance(claims, list):
        for i, claim in enumerate(claims):
            if not isinstance(claim, dict):
                continue
            text = claim.get("claim", "") + " " + claim.get("evidence", "")

            # 检查是否同时出现关联词和因果词（可能存在 hedge 升级）
            has_causal = any(w in text for w in CAUSAL_WORDS)
            has_association = any(w in text for w in ASSOCIATION_WORDS)

            if has_causal and has_association:
                # 检查因果词是否紧跟在关联词之后（可能的 hedge 升级）
                for cw in CAUSAL_WORDS:
                    if cw in text:
                        # 检查因果词前面是否有"不"否定
                        idx = text.find(cw)
                        if idx > 0 and text[idx - 1] == "不":
                            continue  # "不导致"是正确的
                        issues.append(
                            f"key_claims[{i}] 可能存在 hedge 升级：同时出现关联词和因果词 '{cw}'"
                        )
                        break

            # 检查 condition 字段是否有 hedge 限定
            condition = claim.get("condition", "")
            if has_causal and not condition:
                issues.append(
                    f"key_claims[{i}] 使用因果词但无 condition 限定，建议添加 hedge"
                )

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


def _check_author_vs_user(card: Dict) -> Dict[str, Any]:
    """5. 作者 vs 我们检查（作者已证明的 vs 当前研究启发是否混淆）。"""
    issues = []

    # core_answer 应该是作者的观点，不应包含"我们"的主张
    core_answer = card.get("core_answer", "")
    if "我们" in core_answer and "应该" in core_answer:
        issues.append("core_answer 包含'我们应该'，可能混淆了作者观点和研究启发")

    # reusable_inspiration 应该是当前研究启发，不应是作者已证明的
    inspiration = card.get("reusable_inspiration", [])
    if isinstance(inspiration, list):
        for i, insp in enumerate(inspiration):
            if not isinstance(insp, dict):
                continue
            content = insp.get("content", "")
            # 检查是否误将作者的发现放入 inspiration
            if any(w in content for w in ["作者发现", "作者证明", "本研究证明"]):
                issues.append(
                    f"reusable_inspiration[{i}] 可能误将作者发现放入研究启发"
                )

    # key_claims 应该是作者的主张，不应是研究启发
    claims = card.get("key_claims", [])
    if isinstance(claims, list):
        for i, claim in enumerate(claims):
            if not isinstance(claim, dict):
                continue
            text = claim.get("claim", "")
            if any(w in text for w in ["我们可以", "我们应该", "建议未来"]):
                issues.append(
                    f"key_claims[{i}] 包含研究启发词汇，应移入 reusable_inspiration"
                )

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


# ============================================================
# 工具函数
# ============================================================

def _text_similarity(t1: str, t2: str) -> float:
    """计算两段文本的相似度（基于 Jaccard 相似度，分词后计算）。"""
    if not t1 or not t2:
        return 0.0
    # 简单分词：按空格和标点分割
    words1 = set(re.findall(r"[\w]+", t1.lower()))
    words2 = set(re.findall(r"[\w]+", t2.lower()))
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


def _save_audit_result(paper_id: int, quality_score: float, checks: Dict) -> None:
    """保存 audit 结果到数据库。"""
    from datetime import datetime
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        conn.execute(
            "UPDATE paper_knowledge_cards SET quality_score=?, audit_report=? WHERE paper_id=?",
            (quality_score, json.dumps(checks, ensure_ascii=False), paper_id),
        )
        conn.commit()
    finally:
        conn.close()


def run_audit_batch(paper_ids: list[int]) -> List[Dict[str, Any]]:
    """批量质量校验。"""
    results = []
    for pid in paper_ids:
        result = run_audit(pid)
        results.append(result)
        logger.info(
            "paper_id=%d 质量校验完成 score=%.2f passed=%d/5",
            pid,
            result["quality_score"],
            sum(1 for c in result["checks"].values() if c.get("passed")),
        )
    return results
