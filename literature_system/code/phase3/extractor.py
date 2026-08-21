"""论文知识提取器（3.1-3.3）。

基于第二阶段已切好的 paper_sections / paper_figures 表，
通过 LLM 提取知识卡片、方法流程、关键数值。

数据复用原则：
- 知识卡片：按 section_type 查询章节喂给 LLM（intro→research_question, conclusion→core_answer 等）
- 方法流程：直接复用 section_type='methods' 章节
- 数据数值：从 section_type='results' 章节和 fig_type='table' 图表提取
- anchor 锚点：复用 paper_sections.id / paper_figures.id，无需重新定位
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import config
from db import get_connection
from logger import get_logger
from phase3.job_tracker import (
    EXTRACTION_TYPES,
    get_failed_extraction_types,
    get_latest_extraction_status,
    get_papers_needing_extraction,
    record_extraction_status,
    track_extraction,
)

logger = get_logger("phase3.extractor")

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


# ============================================================
# 数据查询：从第二阶段表获取喂给 LLM 的输入
# ============================================================

def _load_prompt(name: str) -> str:
    """加载 Prompt 模板。"""
    path = PROMPTS_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def get_paper_metadata(paper_id: int) -> Dict[str, Any]:
    """获取论文元数据。"""
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, doi, title, abstract, journal, published_date, keywords "
            "FROM papers WHERE id=?",
            (paper_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_sections_by_type(paper_id: int, section_types: List[str]) -> List[Dict[str, Any]]:
    """按 section_type 查询章节切片（核心数据复用）。

    Args:
        paper_id: 论文 ID
        section_types: 章节类型列表（如 ['intro', 'methods', 'results']）

    Returns:
        章节列表，每个章节含 id / section_type / heading / content / page_start / page_end
    """
    if not section_types:
        return []
    placeholders = ",".join("?" * len(section_types))
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT id, section_type, heading, content, page_start, page_end, order_idx "
            f"FROM paper_sections WHERE paper_id=? AND section_type IN ({placeholders}) "
            f"ORDER BY order_idx",
            [paper_id] + section_types,
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_all_sections(paper_id: int) -> List[Dict[str, Any]]:
    """获取论文全部章节。"""
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, section_type, heading, content, page_start, page_end, order_idx "
            "FROM paper_sections WHERE paper_id=? ORDER BY order_idx",
            (paper_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_figures(paper_id: int, fig_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取论文图表（figure/table/equation）。"""
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        if fig_type:
            cur.execute(
                "SELECT id, fig_label, fig_type, caption, file_path, page "
                "FROM paper_figures WHERE paper_id=? AND fig_type=? ORDER BY page",
                (paper_id, fig_type),
            )
        else:
            cur.execute(
                "SELECT id, fig_label, fig_type, caption, file_path, page "
                "FROM paper_figures WHERE paper_id=? ORDER BY page",
                (paper_id,),
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _fallback_to_fulltext(paper_id: int) -> str:
    """章节缺失时回退到 paper_fulltext.full_text。"""
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT full_text FROM paper_fulltext WHERE paper_id=?", (paper_id,))
        row = cur.fetchone()
        return row["full_text"] if row else ""
    finally:
        conn.close()


def _format_sections_for_llm(sections: List[Dict[str, Any]]) -> str:
    """格式化章节列表为 LLM 输入文本。"""
    if not sections:
        return "(无相关章节)"
    lines = []
    for s in sections:
        lines.append(
            f"--- section_id={s['id']} | type={s['section_type']} | "
            f"heading={s.get('heading', '')} | page={s.get('page_start', '?')}-{s.get('page_end', '?')} ---"
        )
        content = s.get("content", "") or ""
        # 截断过长章节（避免超出 LLM 上下文）
        if len(content) > 8000:
            content = content[:8000] + "\n... [章节过长已截断]"
        lines.append(content)
    return "\n".join(lines)


def _format_figures_for_llm(figures: List[Dict[str, Any]]) -> str:
    """格式化图表列表为 LLM 输入文本。"""
    if not figures:
        return "(无图表)"
    lines = []
    for f in figures:
        lines.append(
            f"--- figure_id={f['id']} | label={f.get('fig_label', '')} | "
            f"type={f.get('fig_type', '')} | page={f.get('page', '?')} ---"
        )
        lines.append(f"caption: {f.get('caption', '') or '(无说明)'}")
    return "\n".join(lines)


# ============================================================
# 3.1 知识卡片提取
# ============================================================

@track_extraction("knowledge_card")
def extract_knowledge_card(
    paper_id: int,
    llm_client,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """提取论文知识卡片（6 章节固定结构）。

    数据复用：按 section_type 查询章节喂给 LLM，不重新从 PDF 切分全文。

    Args:
        paper_id: 论文 ID
        llm_client: LLMClient 实例
        force: 是否强制重新提取（覆盖已有结果）

    Returns:
        知识卡片字典（含 research_question / core_answer / key_claims 等）
    """
    # 检查是否已提取
    if not force:
        existing = _get_existing_card(paper_id)
        if existing:
            logger.info("paper_id=%d 已有知识卡片，跳过（force=True 可重新提取）", paper_id)
            return existing

    meta = get_paper_metadata(paper_id)
    if not meta:
        raise ValueError(f"paper_id={paper_id} 不存在")

    # 检查是否为占位论文
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT is_placeholder FROM papers WHERE id=?", (paper_id,))
        row = cur.fetchone()
        if row and row["is_placeholder"] == 1:
            logger.warning("paper_id=%d 为占位论文，跳过提取", paper_id)
            raise ValueError(f"paper_id={paper_id} 为占位论文（标题与内容不匹配），已跳过提取")
    finally:
        conn.close()

    # 按 section_type 精准查询章节（核心数据复用）
    intro = get_sections_by_type(paper_id, ["intro", "introduction"])
    methods = get_sections_by_type(paper_id, ["methods", "methodology", "materials_and_methods"])
    results = get_sections_by_type(paper_id, ["results", "results_and_discussion"])
    discussion = get_sections_by_type(paper_id, ["discussion"])
    conclusion = get_sections_by_type(paper_id, ["conclusion", "conclusions"])
    all_sections = get_all_sections(paper_id)
    figures = get_figures(paper_id)

    # 如果关键章节缺失，回退到全文
    if not all_sections:
        full_text = _fallback_to_fulltext(paper_id)
        if full_text:
            all_sections = [{
                "id": -1,
                "section_type": "fulltext",
                "heading": "Full Text (fallback)",
                "content": full_text[:10000],
                "page_start": None,
                "page_end": None,
            }]

    if not all_sections:
        raise ValueError(f"paper_id={paper_id} 无章节数据，无法提取知识卡片")

    # 论文分类，选择对应的 prompt
    from .paper_classifier import classify_paper, get_prompt_template_name
    paper_type = classify_paper(meta)
    prompt_name = get_prompt_template_name(paper_type, "knowledge_card")
    logger.info(f"paper_id={paper_id} 分类为 {paper_type}，使用 prompt: {prompt_name}")
    
    # 构造 LLM 输入
    system_prompt = _load_prompt(prompt_name)
    user_content = _build_knowledge_card_input(
        meta, intro, methods, results, discussion, conclusion, all_sections, figures
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    logger.info("paper_id=%d 开始提取知识卡片 model=%s", paper_id, llm_client.model)
    # Knowledge cards contain nested claims, evidence anchors and limitations.
    # A 4K output cap regularly truncates otherwise valid DeepSeek JSON, so give
    # this richest extraction type a larger completion budget.
    result = llm_client.chat_json(
        messages,
        max_tokens=max(8192, llm_client.max_tokens),
    )

    # 补充 source_section_ids（如果 LLM 未填）
    if not result.get("source_section_ids"):
        result["source_section_ids"] = [s["id"] for s in all_sections if s["id"] > 0]

    # 评估 quality_score
    from .self_audit import evaluate_quality_score, validate_key_claims
    quality_score = evaluate_quality_score(result)
    result["quality_score"] = quality_score
    logger.info("paper_id=%d quality_score=%.2f", paper_id, quality_score)

    # key_claims 质量校验与二次精炼
    claims_issues = validate_key_claims(result.get("key_claims", []))
    if claims_issues["needs_refinement"] and not force:
        logger.warning("paper_id=%d key_claims 质量不足，进行二次精炼", paper_id)
        result = _refine_key_claims(result, llm_client, messages, meta, all_sections, figures)
        # 重新评估质量分数
        quality_score = evaluate_quality_score(result)
        result["quality_score"] = quality_score
        logger.info("paper_id=%d 精炼后 quality_score=%.2f", paper_id, quality_score)

    # 如果质量分数低于 0.6，自动重试一次
    if quality_score < 0.6 and not force:
        logger.warning("paper_id=%d quality_score=%.2f < 0.6，自动重试一次", paper_id, quality_score)
        result = llm_client.chat_json(messages)
        if not result.get("source_section_ids"):
            result["source_section_ids"] = [s["id"] for s in all_sections if s["id"] > 0]
        quality_score = evaluate_quality_score(result)
        result["quality_score"] = quality_score
        logger.info("paper_id=%d 重试后 quality_score=%.2f", paper_id, quality_score)

    # 落库（2026-08-01：传入 paper_type，使 prompt_version 区分分类）
    _save_knowledge_card(paper_id, result, llm_client.model, paper_type=paper_type)
    logger.info("paper_id=%d 知识卡片提取完成 claims=%d",
                paper_id, len(result.get("key_claims", [])))
    return result


def _refine_key_claims(
    result: Dict[str, Any],
    llm_client,
    original_messages: List[Dict],
    meta: Dict,
    all_sections: List,
    figures: List,
) -> Dict[str, Any]:
    """对 key_claims 进行二次精炼。

    针对缺少具体数值、证据不足或 anchor 缺失的 key_claims，
    调用轻量级 LLM 进行精炼。

    Args:
        result: 原始知识卡片结果
        llm_client: LLMClient 实例
        original_messages: 原始 LLM 消息
        meta: 论文元数据
        all_sections: 所有章节
        figures: 所有图表

    Returns:
        精炼后的知识卡片字典
    """
    from .self_audit import validate_key_claims

    key_claims = result.get("key_claims", [])
    if not isinstance(key_claims, list) or not key_claims:
        return result

    # 识别需要精炼的 claims
    issues = validate_key_claims(key_claims)
    if not issues["needs_refinement"]:
        return result

    # 构造精炼 Prompt
    refinement_prompt = """你是一个学术论文知识提炼专家。请对以下 key_claims 进行精炼，确保每条 claim 都包含：
1. 具体数值（如 p<0.05、95% CI、效应量等）
2. 明确的证据来源
3. 有效的 anchor（section_id 或 figure_id）

原始 key_claims：
{claims}

论文元数据：
- 标题: {title}
- 章节 ID 列表: {section_ids}
- 图表 ID 列表: {figure_ids}

请返回精炼后的完整 key_claims 列表（JSON 格式），每条 claim 必须包含：
- claim: 核心主张（必须包含具体数值）
- evidence: 证据描述（必须包含统计显著性）
- anchor: {{"section_id": ...}} 或 {{"figure_id": ...}}
- condition: 适用条件/边界

只返回 key_claims 列表，不要返回其他内容。
""".format(
        claims=json.dumps(key_claims, ensure_ascii=False, indent=2),
        title=meta.get("title", ""),
        section_ids=[s["id"] for s in all_sections if s.get("id") and s["id"] > 0],
        figure_ids=[f["id"] for f in figures if f.get("id")],
    )

    try:
        logger.info("paper_id 精炼 key_claims，共 %d 条原始 claims", len(key_claims))
        refined_messages = [
            {"role": "system", "content": refinement_prompt},
            {"role": "user", "content": "请精炼上述 key_claims"},
        ]
        refined_result = llm_client.chat_json(refined_messages)

        # 合并精炼结果
        if isinstance(refined_result, dict) and "key_claims" in refined_result:
            refined_claims = refined_result["key_claims"]
            if isinstance(refined_claims, list) and len(refined_claims) >= len(key_claims):
                result["key_claims"] = refined_claims
                logger.info("paper_id key_claims 精炼完成，%d 条 → %d 条",
                           len(key_claims), len(refined_claims))
            else:
                logger.warning("paper_id 精炼后 key_claims 数量减少，保留原始结果")
        elif isinstance(refined_result, list):
            result["key_claims"] = refined_result
            logger.info("paper_id key_claims 精炼完成（直接返回列表）")

    except Exception as e:
        logger.warning("paper_id key_claims 精炼失败: %s，保留原始结果", e)

    return result


def _build_knowledge_card_input(
    meta: Dict,
    intro: List, methods: List, results: List,
    discussion: List, conclusion: List,
    all_sections: List, figures: List,
) -> str:
    """构造知识卡片提取的 LLM 输入。"""
    lines = [
        f"# 论文元数据",
        f"paper_id: {meta.get('id', '')}",
        f"DOI: {meta.get('doi', '')}",
        f"标题: {meta.get('title', '')}",
        f"期刊: {meta.get('journal', '')}",
        f"发表日期: {meta.get('published_date', '')}",
        f"关键词: {meta.get('keywords', '')}",
        "",
        "# 章节切片（用于锚点引用的 section_id）",
        _format_sections_for_llm(all_sections),
        "",
        "# 图表数据（用于锚点引用的 figure_id）",
        _format_figures_for_llm(figures),
        "",
        "# 重点章节（按 section_type 查询，直接用于提取）",
        "## Introduction 章节（用于提取 research_question）",
        _format_sections_for_llm(intro) if intro else "(无 intro 章节)",
        "",
        "## Methods 章节（用于提取 evidence_generation）",
        _format_sections_for_llm(methods) if methods else "(无 methods 章节)",
        "",
        "## Results 章节（用于提取 key_claims）",
        _format_sections_for_llm(results) if results else "(无 results 章节)",
        "",
        "## Discussion 章节（用于提取 boundaries）",
        _format_sections_for_llm(discussion) if discussion else "(无 discussion 章节)",
        "",
        "## Conclusion 章节（用于提取 core_answer）",
        _format_sections_for_llm(conclusion) if conclusion else "(无 conclusion 章节)",
    ]
    return "\n".join(lines)


def _get_existing_card(paper_id: int) -> Optional[Dict]:
    """查询已存在的知识卡片。"""
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM paper_knowledge_cards WHERE paper_id=?",
            (paper_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        card = dict(row)
        # 解析 JSON 字段
        for k in ["key_claims", "boundaries", "reusable_inspiration", "source_section_ids", "audit_report"]:
            if card.get(k) and isinstance(card[k], str):
                try:
                    card[k] = json.loads(card[k])
                except json.JSONDecodeError:
                    pass
        return card
    finally:
        conn.close()


def _save_knowledge_card(paper_id: int, card: Dict, model_name: str, paper_type: str = "experimental") -> None:
    """保存知识卡片到数据库。

    Args:
        paper_id: 论文 ID
        card: 知识卡片字典
        model_name: LLM 模型名称
        paper_type: 论文分类（review/methodology/experimental/data_description），
            用于构造可区分的 prompt_version，如 `v1-review` / `v1-experimental`。
    """
    extraction_method = f"{model_name}+{config.PHASE3_PROMPT_VERSION}"
    extracted_at = datetime.now().isoformat()
    # 2026-08-01：将 paper_type 拼接到 prompt_version，区分不同分类使用的模板
    prompt_version = f"{config.PHASE3_PROMPT_VERSION}-{paper_type}"

    conn = get_connection(init_schema=False, row_factory=False)
    try:
        conn.execute(
            """INSERT OR REPLACE INTO paper_knowledge_cards
               (paper_id, research_question, core_answer, key_claims, evidence_generation,
                boundaries, reusable_inspiration, source_section_ids, extraction_method,
                extracted_at, quality_score, audit_report, prompt_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                paper_id,
                card.get("research_question", ""),
                card.get("core_answer", ""),
                json.dumps(card.get("key_claims", []), ensure_ascii=False),
                card.get("evidence_generation", ""),
                json.dumps(card.get("boundaries", {}), ensure_ascii=False),
                json.dumps(card.get("reusable_inspiration", []), ensure_ascii=False),
                json.dumps(card.get("source_section_ids", []), ensure_ascii=False),
                extraction_method,
                extracted_at,
                card.get("quality_score"),
                json.dumps(card.get("audit_report", {}), ensure_ascii=False),
                prompt_version,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================
# 3.2 方法流程提取
# ============================================================

@track_extraction("methods")
def extract_methods(
    paper_id: int,
    llm_client,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """提取论文方法流程。 paper_sections.methods 章节）。

    Args:
        paper_id: 论文 ID
        llm_client: LLMClient 实例
        force: 是否强制重新提取

    Returns:
        方法流程字典（含 methodology / workflow / data_sources 等）
    """
    if not force:
        existing = _get_existing_methods(paper_id)
        if existing:
            logger.info("paper_id=%d 已有方法流程，跳过", paper_id)
            return existing

    meta = get_paper_metadata(paper_id)
    if not meta:
        raise ValueError(f"paper_id={paper_id} 不存在")

    # 复用 methods 章节
    methods_sections = get_sections_by_type(
        paper_id, ["methods", "methodology", "materials_and_methods"]
    )

    if not methods_sections:
        # 回退到全文
        full_text = _fallback_to_fulltext(paper_id)
        if full_text:
            methods_sections = [{
                "id": -1,
                "section_type": "fulltext_fallback",
                "heading": "Full Text (fallback)",
                "content": full_text[:10000],
                "page_start": None,
                "page_end": None,
            }]
        else:
            raise ValueError(f"paper_id={paper_id} 无 methods 章节且无全文")

    # 论文分类 → 选择 prompt
    from .paper_classifier import classify_paper, get_prompt_template_name
    paper_type = classify_paper(meta)
    prompt_name = get_prompt_template_name(paper_type, "methods")
    logger.info(f"paper_id={paper_id} 分类为 {paper_type}，使用 prompt: {prompt_name}")
    system_prompt = _load_prompt(prompt_name)
    methods_section_id = methods_sections[0]["id"] if methods_sections else None
    user_content = _build_methods_input(meta, methods_sections)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    logger.info("paper_id=%d 开始提取方法流程", paper_id)
    result = llm_client.chat_json(messages)
    result["methods_section_id"] = methods_section_id

    # 2026-08-01：非实验类论文若 evaluation_metrics 为空，写入 "not_applicable"
    # 避免被统计为缺失字段。
    _normalize_evaluation_metrics(result, paper_type)

    _save_methods(paper_id, result, llm_client.model)
    logger.info("paper_id=%d 方法流程提取完成 steps=%d",
                paper_id, len(result.get("workflow", [])))
    return result


def _normalize_evaluation_metrics(methods: Dict, paper_type: str) -> None:
    """对非实验类论文，将空 evaluation_metrics 写为 "not_applicable"。

    适用 paper_type:
    - review: 综述类，可能无偏倚风险评估工具
    - methodology: 方法学类，可能无显式评估指标
    - data_description: 数据描述类，通常无评估指标

    Args:
        methods: LLM 提取的方法字典（原地修改）
        paper_type: classify_paper() 返回的论文类型
    """
    if paper_type not in ("review", "methodology", "data_description"):
        return  # experimental 保持原样

    metrics = methods.get("evaluation_metrics")
    is_empty = (
        metrics is None
        or metrics == ""
        or metrics == []
        or metrics == "[]"
        or metrics == "not_applicable"
    )
    if is_empty:
        methods["evaluation_metrics"] = "not_applicable"


def _build_methods_input(meta: Dict, methods_sections: List) -> str:
    """构造方法流程提取的 LLM 输入。"""
    return "\n".join([
        f"# 论文元数据",
        f"paper_id: {meta.get('id', '')}",
        f"DOI: {meta.get('doi', '')}",
        f"标题: {meta.get('title', '')}",
        f"期刊: {meta.get('journal', '')}",
        "",
        "# Methods 章节（复用 paper_sections.methods）",
        _format_sections_for_llm(methods_sections),
    ])


def _get_existing_methods(paper_id: int) -> Optional[Dict]:
    """查询已存在的方法流程。"""
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM paper_methods WHERE paper_id=?", (paper_id,))
        row = cur.fetchone()
        if not row:
            return None
        result = dict(row)
        for k in ["workflow", "data_sources", "models_algorithms", "evaluation_metrics"]:
            if result.get(k) and isinstance(result[k], str):
                try:
                    result[k] = json.loads(result[k])
                except json.JSONDecodeError:
                    pass
        return result
    finally:
        conn.close()


def _save_methods(paper_id: int, methods: Dict, model_name: str) -> None:
    """保存方法流程到数据库。"""
    extraction_method = f"{model_name}+{config.PHASE3_PROMPT_VERSION}"
    extracted_at = datetime.now().isoformat()

    # 2026-08-01：evaluation_metrics 允许是字符串 "not_applicable"，
    # 落库时统一序列化为 JSON 字符串，保证下游解析一致性。
    evaluation_metrics = methods.get("evaluation_metrics", [])
    if isinstance(evaluation_metrics, str):
        # 已是字符串（如 "not_applicable"），无需 JSON 包装
        evaluation_metrics_serialized = evaluation_metrics
    else:
        evaluation_metrics_serialized = json.dumps(evaluation_metrics, ensure_ascii=False)

    conn = get_connection(init_schema=False, row_factory=False)
    try:
        conn.execute(
            """INSERT OR REPLACE INTO paper_methods
               (paper_id, methodology, workflow, data_sources, models_algorithms,
                evaluation_metrics, methods_section_id, extraction_method, extracted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                paper_id,
                methods.get("methodology", ""),
                json.dumps(methods.get("workflow", []), ensure_ascii=False),
                json.dumps(methods.get("data_sources", {}), ensure_ascii=False),
                json.dumps(methods.get("models_algorithms", []), ensure_ascii=False),
                evaluation_metrics_serialized,
                methods.get("methods_section_id"),
                extraction_method,
                extracted_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================
# 3.3 数据数值提取
# ============================================================

@track_extraction("data_points")
def extract_data_points(
    paper_id: int,
    llm_client,
    *,
    force: bool = False,
) -> List[Dict[str, Any]]:
    """提取论文关键数值（复用 results 章节和表格图表）。

    Args:
        paper_id: 论文 ID
        llm_client: LLMClient 实例
        force: 是否强制重新提取

    Returns:
        数值列表（每个数值含 metric_name / metric_value / unit / anchor 等）
    """
    if not force:
        existing = _get_existing_data_points(paper_id)
        if existing:
            logger.info("paper_id=%d 已有 %d 条数值，跳过", paper_id, len(existing))
            return existing

    meta = get_paper_metadata(paper_id)
    if not meta:
        raise ValueError(f"paper_id={paper_id} 不存在")

    # 复用 results 章节 + 表格图表
    results_sections = get_sections_by_type(paper_id, ["results", "results_and_discussion"])
    tables = get_figures(paper_id, fig_type="table")

    if not results_sections:
        # 回退到全文
        full_text = _fallback_to_fulltext(paper_id)
        if full_text:
            results_sections = [{
                "id": -1,
                "section_type": "fulltext_fallback",
                "heading": "Full Text (fallback)",
                "content": full_text[:10000],
                "page_start": None,
                "page_end": None,
            }]
        else:
            raise ValueError(f"paper_id={paper_id} 无 results 章节且无全文")

    system_prompt = _load_prompt("data_points_v1")
    user_content = _build_data_points_input(meta, results_sections, tables)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    logger.info("paper_id=%d 开始提取数据数值", paper_id)
    result = llm_client.chat_json(messages)

    # chat_json 返回的是 dict，但 data_points 应该是 list
    # 处理 LLM 可能返回 {"data_points": [...]} / {"extracted_values": [...]} / {"data": [...]} 的情况
    if isinstance(result, dict):
        data_points = result.get("data_points") or result.get("extracted_values") or result.get("data", [])
    else:
        data_points = result

    if not isinstance(data_points, list):
        data_points = [data_points] if data_points else []

    _save_data_points(paper_id, data_points, llm_client.model)
    logger.info("paper_id=%d 数据数值提取完成 count=%d", paper_id, len(data_points))
    return data_points


def _build_data_points_input(
    meta: Dict, results_sections: List, tables: List,
) -> str:
    """构造数据数值提取的 LLM 输入。"""
    return "\n".join([
        f"# 论文元数据",
        f"paper_id: {meta.get('id', '')}",
        f"DOI: {meta.get('doi', '')}",
        f"标题: {meta.get('title', '')}",
        "",
        "# Results 章节（复用 paper_sections.results）",
        _format_sections_for_llm(results_sections),
        "",
        "# 表格数据（复用 paper_figures WHERE fig_type='table'）",
        _format_figures_for_llm(tables) if tables else "(无表格)",
    ])


def _get_existing_data_points(paper_id: int) -> List[Dict]:
    """查询已存在的数据数值。"""
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM paper_data_points WHERE paper_id=? ORDER BY id",
            (paper_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _save_data_points(paper_id: int, data_points: List[Dict], model_name: str) -> None:
    """保存数据数值到数据库（先删除旧数据再插入）。"""
    from .metric_normalizer import normalize_metric_name, parse_metric_value
    
    extraction_method = f"{model_name}+{config.PHASE3_PROMPT_VERSION}"
    extracted_at = datetime.now().isoformat()

    conn = get_connection(init_schema=False, row_factory=False)
    try:
        # 先删除旧数据
        conn.execute("DELETE FROM paper_data_points WHERE paper_id=?", (paper_id,))

        for dp in data_points:
            metric_name = dp.get("metric_name", "")
            metric_value_raw = dp.get("metric_value")
            
            # 解析数值（支持范围、不等式、文本）
            metric_value_numeric, metric_value_original = parse_metric_value(metric_value_raw)
            
            # 归一化指标名
            metric_name_normalized = normalize_metric_name(metric_name)
            
            conn.execute(
                """INSERT INTO paper_data_points
                   (paper_id, metric_name, metric_value, metric_value_numeric, 
                    metric_value_original, metric_name_normalized,
                    unit, context, section_id, figure_id, page, significance, 
                    confidence, is_review_record, extraction_method, extracted_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    paper_id,
                    metric_name,
                    metric_value_raw,  # metric_value 改为 TEXT 类型
                    metric_value_numeric,
                    metric_value_original,
                    metric_name_normalized,
                    dp.get("unit", ""),
                    dp.get("context", ""),
                    dp.get("section_id"),
                    dp.get("figure_id"),
                    dp.get("page"),
                    dp.get("significance", ""),
                    dp.get("confidence", "medium"),
                    int(bool(dp.get("is_review_record", 0))),
                    extraction_method,
                    extracted_at,
                ),
            )
        conn.commit()
    finally:
        conn.close()


# ============================================================
# 批量提取入口
# ============================================================

def extract_all(
    paper_id: int,
    llm_client=None,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """对单篇论文执行 3.1-3.3 全部提取。

    Args:
        paper_id: 论文 ID
        llm_client: LLMClient 实例（None 时自动创建）
        force: 是否强制重新提取

    Returns:
        {"card": ..., "methods": ..., "data_points": ...}
    """
    if llm_client is None:
        from .llm_client import LLMClient
        llm_client = LLMClient()

    results: Dict[str, Any] = {}

    # 3.1 + 3.2 并行执行，减少单篇论文总耗时
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_card = executor.submit(extract_knowledge_card, paper_id, llm_client, force=force)
        future_methods = executor.submit(extract_methods, paper_id, llm_client, force=force)

        try:
            results["card"] = future_card.result()
        except Exception as e:
            logger.error("3.1 知识卡片提取失败 paper_id=%d: %s", paper_id, e)
            results["card_error"] = str(e)

        try:
            results["methods"] = future_methods.result()
        except Exception as e:
            logger.error("3.2 方法流程提取失败 paper_id=%d: %s", paper_id, e)
            results["methods_error"] = str(e)

    # 3.3 数据数值（预检：无 results 章节且无表格时跳过，避免无效 LLM 调用）
    try:
        results_sections = get_sections_by_type(
            paper_id, ["results", "results_and_discussion"]
        )
        tables = get_figures(paper_id, fig_type="table")
        if results_sections or tables:
            results["data_points"] = extract_data_points(paper_id, llm_client, force=force)
        else:
            logger.info("paper_id=%d 无 results 章节和表格，跳过数据数值提取", paper_id)
            record_extraction_status(
                paper_id, "data_points", "skipped",
                error_msg="无 results 章节且无表格，无需提取数据数值",
            )
            results["data_points"] = []
    except Exception as e:
        logger.error("3.3 数据数值提取失败 paper_id=%d: %s", paper_id, e)
        results["data_points_error"] = str(e)

    return results


def extract_missing(
    paper_id: int,
    llm_client=None,
    *,
    force: bool = False,
    parent_job_id: Optional[int] = None,
) -> Dict[str, Any]:
    """仅对失败或缺失的提取类型执行提取（用于重试）。

    若 force=True，则强制重新提取全部三种类型。
    """
    if llm_client is None:
        from .llm_client import LLMClient
        llm_client = LLMClient()

    if force:
        return extract_all_in_one(paper_id, llm_client, force=True, parent_job_id=parent_job_id)

    results: Dict[str, Any] = {}
    failed_types = get_failed_extraction_types(paper_id)

    # 若没有任何 job 记录，按全部缺失处理
    if not failed_types and not any(
        get_latest_extraction_status(paper_id, et) for et in EXTRACTION_TYPES
    ):
        return extract_all_in_one(paper_id, llm_client, force=False, parent_job_id=parent_job_id)

    if "knowledge_card" in failed_types:
        try:
            results["card"] = extract_knowledge_card(
                paper_id, llm_client, force=False, parent_job_id=parent_job_id
            )
        except Exception as e:
            logger.error("重试知识卡片失败 paper_id=%d: %s", paper_id, e)
            results["card_error"] = str(e)
    if "methods" in failed_types:
        try:
            results["methods"] = extract_methods(
                paper_id, llm_client, force=False, parent_job_id=parent_job_id
            )
        except Exception as e:
            logger.error("重试方法流程失败 paper_id=%d: %s", paper_id, e)
            results["methods_error"] = str(e)
    if "data_points" in failed_types:
        try:
            results_sections = get_sections_by_type(
                paper_id, ["results", "results_and_discussion"]
            )
            tables = get_figures(paper_id, fig_type="table")
            if results_sections or tables:
                results["data_points"] = extract_data_points(
                    paper_id, llm_client, force=False, parent_job_id=parent_job_id
                )
            else:
                record_extraction_status(
                    paper_id, "data_points", "skipped",
                    error_msg="无 results 章节且无表格，无需提取数据数值",
                )
                results["data_points"] = []
        except Exception as e:
            logger.error("重试数据数值失败 paper_id=%d: %s", paper_id, e)
            results["data_points_error"] = str(e)

    return results


def extract_batch(
    paper_ids: List[int],
    llm_client=None,
    *,
    force: bool = False,
) -> Dict[int, Dict[str, Any]]:
    """批量提取多篇论文的 3.1-3.3 数据。

    Args:
        paper_ids: 论文 ID 列表
        llm_client: LLMClient 实例（None 时自动创建）
        force: 是否强制重新提取

    Returns:
        {paper_id: {"card": ..., "methods": ..., "data_points": ...}}
    """
    if llm_client is None:
        from .llm_client import LLMClient
        llm_client = LLMClient()

    all_results: Dict[int, Dict[str, Any]] = {}
    for i, pid in enumerate(paper_ids, 1):
        logger.info("批量提取进度 %d/%d paper_id=%d", i, len(paper_ids), pid)
        all_results[pid] = extract_all(pid, llm_client, force=force)
    return all_results


def _build_all_in_one_input(
    meta: Dict,
    all_sections: List,
    methods_sections: List,
    results_sections: List,
    figures: List,
    tables: List,
) -> str:
    """构造一次性提炼的 LLM 输入。"""
    lines = [
        f"# 论文元数据",
        f"paper_id: {meta.get('id', '')}",
        f"DOI: {meta.get('doi', '')}",
        f"标题: {meta.get('title', '')}",
        f"期刊: {meta.get('journal', '')}",
        f"发表日期: {meta.get('published_date', '')}",
        f"关键词: {meta.get('keywords', '')}",
        "",
        "# 全部章节切片（用于知识卡片与锚点）",
        _format_sections_for_llm(all_sections) if all_sections else "(无章节)",
        "",
        "# 图表数据",
        _format_figures_for_llm(figures) if figures else "(无图表)",
        "",
        "# Methods 章节（用于提取方法流程）",
        _format_sections_for_llm(methods_sections) if methods_sections else "(无 methods 章节)",
        "",
        "# Results 章节（用于提取数据数值）",
        _format_sections_for_llm(results_sections) if results_sections else "(无 results 章节)",
        "",
        "# 表格数据（用于提取数据数值）",
        _format_figures_for_llm(tables) if tables else "(无表格)",
    ]
    return "\n".join(lines)


def extract_all_in_one(
    paper_id: int,
    llm_client=None,
    *,
    force: bool = False,
    parent_job_id: Optional[int] = None,
) -> Dict[str, Any]:
    """对单篇论文执行 3.1-3.3 全部提取，合并为一次 LLM 调用。

    预期将远程调用次数从 3 次降为 1 次，显著减少总耗时。

    Args:
        paper_id: 论文 ID
        llm_client: LLMClient 实例（None 时自动创建）
        force: 是否强制重新提取

    Returns:
        {"card": ..., "methods": ..., "data_points": ...}
    """
    if llm_client is None:
        from .llm_client import LLMClient
        llm_client = LLMClient()

    existing_card = _get_existing_card(paper_id)
    existing_methods = _get_existing_methods(paper_id)
    existing_data_points = _get_existing_data_points(paper_id)

    if not force and existing_card and existing_methods and existing_data_points is not None:
        logger.info("paper_id=%d 已有完整提炼结果，跳过（force=True 可重新提取）", paper_id)
        # 补录 extract 状态，避免 get_papers_needing_extraction 反复选中
        for et in EXTRACTION_TYPES:
            record_extraction_status(paper_id, et, "done")
        return {
            "card": existing_card,
            "methods": existing_methods,
            "data_points": existing_data_points,
        }

    meta = get_paper_metadata(paper_id)
    if not meta:
        raise ValueError(f"paper_id={paper_id} 不存在")

    all_sections = get_all_sections(paper_id)
    methods_sections = get_sections_by_type(
        paper_id, ["methods", "methodology", "materials_and_methods"]
    )
    results_sections = get_sections_by_type(
        paper_id, ["results", "results_and_discussion"]
    )
    figures = get_figures(paper_id)
    tables = get_figures(paper_id, fig_type="table")

    # 章节缺失时回退到全文
    if not all_sections:
        full_text = _fallback_to_fulltext(paper_id)
        if full_text:
            all_sections = [{
                "id": -1,
                "section_type": "fulltext",
                "heading": "Full Text (fallback)",
                "content": full_text[:10000],
                "page_start": None,
                "page_end": None,
            }]

    if not all_sections:
        raise ValueError(f"paper_id={paper_id} 无章节数据，无法提取")

    methods_section_id = methods_sections[0]["id"] if methods_sections else None

    # 记录三种提取类型开始
    for et in EXTRACTION_TYPES:
        record_extraction_status(paper_id, et, "running", parent_job_id=parent_job_id)

    system_prompt = _load_prompt("paper_all_in_one_v1")
    user_content = _build_all_in_one_input(
        meta, all_sections, methods_sections, results_sections, figures, tables
    )

    # 输入过长时直接回退分次提取，避免单次 LLM 上下文/超时压力
    MAX_ALL_IN_ONE_INPUT_CHARS = 30000
    if len(user_content) > MAX_ALL_IN_ONE_INPUT_CHARS:
        logger.info(
            "paper_id=%d 合并输入过长(%d 字符)，改用分次提取",
            paper_id, len(user_content),
        )
        return extract_all(paper_id, llm_client, force=True)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    logger.info(
        "paper_id=%d 开始一次性提炼 model=%s input_chars=%d",
        paper_id, llm_client.model, len(user_content),
    )
    try:
        result = llm_client.chat_json(messages)
    except Exception as e:
        for et in EXTRACTION_TYPES:
            record_extraction_status(
                paper_id, et, "failed",
                error_msg=str(e)[:500],
                error_class=e.__class__.__name__,
            )
        # 合并调用失败（JSON 解析/超时/输出截断），回退到分次提取
        logger.warning(
            "paper_id=%d 一次性提炼失败，回退到分次提取: %s",
            paper_id, e,
        )
        return extract_all(paper_id, llm_client, force=True)

    # 解析三部分
    card = result.get("knowledge_card", {})
    methods = result.get("methods", {})
    data_points_result = result.get("data_points", {})
    if isinstance(data_points_result, dict):
        data_points = data_points_result.get("data_points", [])
    elif isinstance(data_points_result, list):
        data_points = data_points_result
    else:
        data_points = []

    # 补充缺失的锚点/ID
    if not card.get("source_section_ids"):
        card["source_section_ids"] = [s["id"] for s in all_sections if s["id"] > 0]
    methods["methods_section_id"] = methods_section_id

    # 落库
    _save_knowledge_card(paper_id, card, llm_client.model)
    _save_methods(paper_id, methods, llm_client.model)
    _save_data_points(paper_id, data_points, llm_client.model)

    # 记录三种提取类型完成
    for et in EXTRACTION_TYPES:
        record_extraction_status(paper_id, et, "done")

    logger.info(
        "paper_id=%d 一次性提炼完成 claims=%d steps=%d data_points=%d",
        paper_id,
        len(card.get("key_claims", [])),
        len(methods.get("workflow", [])),
        len(data_points),
    )
    return {"card": card, "methods": methods, "data_points": data_points}


def get_papers_with_fulltext() -> List[int]:
    """获取所有有全文数据的论文 ID（用于批量提取）。"""
    conn = get_connection(init_schema=False, row_factory=False)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT paper_id FROM paper_sections "
            "UNION SELECT DISTINCT paper_id FROM paper_fulltext "
            "ORDER BY paper_id"
        )
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()
