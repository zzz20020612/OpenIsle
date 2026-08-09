"""Prompt A/B 实验脚本：v1 vs v2 双盲对比。

做法：
1. 选 N 篇非占位论文作为对照集（覆盖 review / methodology / experimental）。
2. 对每篇论文，分别用 v1 和 v2 Prompt 跑 extract_missing，记录结果。
3. 收集 quality_score / extract_duration / 字段完整率。
4. 输出 Markdown 对比报告到 docs/eval_reports/prompt_v1_v2_YYYYMM.md。

用法：
    python scripts/run_prompt_ab_test.py --limit 5 --paper-ids 33,36,37,39,41
    python scripts/run_prompt_ab_test.py --limit 10  # 自动从数据库选
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from db import get_connection
from logger import get_logger

logger = get_logger("scripts.prompt_ab_test")


def select_papers(limit: int, paper_ids: list[int] | None) -> list[int]:
    """选择对照论文 ID 列表。

    优先级：--paper-ids > 数据库选 limit 篇非占位论文（按 id 升序，取最早入库的）。
    """
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        if paper_ids:
            placeholders = ",".join("?" * len(paper_ids))
            cur.execute(
                f"""
                SELECT id, title, is_placeholder
                FROM papers
                WHERE id IN ({placeholders})
                ORDER BY id
                """,
                paper_ids,
            )
        else:
            cur.execute(
                """
                SELECT id, title, is_placeholder
                FROM papers
                WHERE COALESCE(is_placeholder, 0) = 0
                  AND id IN (SELECT DISTINCT paper_id FROM paper_sections)
                ORDER BY id
                LIMIT ?
                """,
                (limit,),
            )
        return [r["id"] for r in cur.fetchall()]
    finally:
        conn.close()


def get_quality_stats(paper_id: int) -> dict:
    """从数据库读取指定论文的提取结果统计。"""
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT quality_score, prompt_version, extracted_at
            FROM paper_knowledge_cards
            WHERE paper_id = ?
            ORDER BY extracted_at DESC LIMIT 1
            """,
            (paper_id,),
        )
        kc = cur.fetchone()
        cur.execute(
            "SELECT COUNT(*) AS c FROM paper_methods WHERE paper_id = ?",
            (paper_id,),
        )
        methods_count = cur.fetchone()["c"]
        cur.execute(
            "SELECT COUNT(*) AS c FROM paper_data_points WHERE paper_id = ?",
            (paper_id,),
        )
        dp_count = cur.fetchone()["c"]
        return {
            "quality_score": kc["quality_score"] if kc else None,
            "prompt_version": kc["prompt_version"] if kc else None,
            "kc_extracted_at": kc["extracted_at"] if kc else None,
            "methods_count": methods_count,
            "dp_count": dp_count,
        }
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Prompt v1 vs v2 A/B 实验")
    parser.add_argument("--limit", type=int, default=5, help="选几篇论文（默认 5）")
    parser.add_argument(
        "--paper-ids",
        type=str,
        default=None,
        help="指定论文 ID 列表，逗号分隔（优先级高于 --limit）",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="报告输出路径（默认 docs/eval_reports/prompt_v1_v2_YYYYMMDD.md）",
    )
    args = parser.parse_args()

    paper_ids_arg = (
        [int(x) for x in args.paper_ids.split(",") if x.strip()]
        if args.paper_ids
        else None
    )
    paper_ids = select_papers(args.limit, paper_ids_arg)
    logger.info(f"对照论文: {paper_ids}")

    if not paper_ids:
        logger.error("未找到可用的对照论文")
        return

    # 步骤 1：备份当前 prompt_version 状态
    logger.info("步骤 1: 备份当前数据库的 prompt_version 状态")
    backup = {pid: get_quality_stats(pid) for pid in paper_ids}
    logger.info(f"  备份: {json.dumps(backup, ensure_ascii=False, default=str)}")

    # 步骤 2：用 v1 跑（如果当前已经是 v1-data_description / v1-methodology，则无需重跑，直接读取现状）
    # 为了简化，本脚本暂只做"读取对比"，不实际重跑 LLM（避免成本）
    # 实际重跑 LLM 的逻辑见 scripts/run_prompt_ab_test_live.py（待实现）
    logger.info("步骤 2: 读取当前 v1 提取结果（来自 paper_knowledge_cards）")
    v1_results = {pid: get_quality_stats(pid) for pid in paper_ids}

    # 步骤 3：用 v2 跑（占位：本脚本仅记录"待运行 v2 提取"的提示）
    logger.info("步骤 3: 标记 v2 提取任务（实际运行需 scripts/run_prompt_ab_test_live.py）")
    v2_results = {
        pid: {
            "quality_score": None,
            "prompt_version": "v2-pending",
            "kc_extracted_at": None,
            "methods_count": None,
            "dp_count": None,
        }
        for pid in paper_ids
    }

    # 步骤 4：生成对比报告
    today = datetime.now().strftime("%Y%m%d")
    out_path = (
        Path(args.out)
        if args.out
        else Path(__file__).resolve().parent.parent / "docs" / "eval_reports" / f"prompt_v1_v2_{today}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Prompt v1 vs v2 A/B 实验报告",
        "",
        f"**生成时间**: {datetime.now().isoformat(timespec='seconds')}",
        f"**对照论文数**: {len(paper_ids)}",
        f"**论文 ID 列表**: {', '.join(str(p) for p in paper_ids)}",
        "",
        "## v1 vs v2 关键差异",
        "",
        "| 维度 | v1 | v2 |",
        "|------|----|----|",
        "| 字符偏移 (start_char / end_char) | ❌ 不要求 | ✅ 强制 |",
        "| key_claims 具体数值 | ⚠️ 隐含鼓励 | ✅ 强制至少 1 个 |",
        "| counter_evidence | ❌ 无 | ✅ 强制填 |",
        "| sample_size 具体数字 | ⚠️ 鼓励 | ✅ 强制 |",
        "| evaluation_metrics.scope | ❌ 无 | ✅ 必填 |",
        "| data_points.confidence | ⚠️ 字符串 high/medium/low | ✅ 强制 0-1 浮点 |",
        "| metric_name ontology | ⚠️ 自由命名 | ✅ 强制对齐 |",
        "",
        "## 对照论文结果",
        "",
        "| paper_id | v1 quality_score | v1 prompt_version | v1 methods | v1 data_points | v2 quality_score | v2 methods | v2 data_points |",
        "|----------|------------------|-------------------|------------|----------------|------------------|------------|----------------|",
    ]
    for pid in paper_ids:
        v1 = v1_results[pid]
        v2 = v2_results[pid]
        lines.append(
            f"| {pid} | {v1['quality_score']} | {v1['prompt_version']} | "
            f"{v1['methods_count']} | {v1['dp_count']} | "
            f"{v2['quality_score']} | {v2['methods_count']} | {v2['dp_count']} |"
        )

    lines.extend(
        [
            "",
            "## 后续步骤",
            "",
            "1. 实现 `scripts/run_prompt_ab_test_live.py`：实际调用 LLM 跑 v2 提取，",
            "   写入临时表（`paper_knowledge_cards_ab_v2` / `paper_methods_ab_v2` / `paper_data_points_ab_v2`）",
            "   以避免污染生产数据。",
            "2. v2 跑完后，对比两组的 quality_score / 字段完整率 / 人工评分。",
            "3. 若 v2 显著胜出（p < 0.05），更新 `config.PHASE3_PROMPT_VERSION = 'v2'` 并迁移生产。",
            "4. 评估指标定义：",
            "   - 字段完整率：知识卡片 7 个核心字段非空率",
            "   - key_claims 含数值率：含具体百分数/效应大小/p 值的主张占比",
            "   - 字符偏移有效率：start_char / end_char 能在 section.content 内定位的比例",
            "",
            "## 关联文件",
            "",
            "- `code/phase3/prompts/knowledge_card_v2.txt`",
            "- `code/phase3/prompts/methods_v2.txt`",
            "- `code/phase3/prompts/data_points_v2.txt`",
        ]
    )

    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"报告已写入: {out_path}")
    print(f"\n报告路径: {out_path}")


if __name__ == "__main__":
    main()
