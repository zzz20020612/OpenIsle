"""回填历史知识卡片的 quality_score。

对已有知识卡片重新运行 self_audit，计算 quality_score 并更新到数据库。

用法：
    python scripts/backfill_quality_score.py [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 添加 code 目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from db import get_connection
from logger import get_logger
from phase3.self_audit import (
    evaluate_quality_score,
    _check_completeness,
    _check_no_duplicate,
    _check_anchor_valid,
    _check_hedge_honesty,
    _check_author_vs_user,
)

logger = get_logger("scripts.backfill_quality_score")


def _build_audit_report(paper_id: int, card: dict) -> dict:
    """直接对内存中的 card 调用 5 项 check，复用 run_audit 逻辑但避免重复读 DB。

    Args:
        paper_id: 论文 ID（用于 anchor_valid 校验）
        card: 知识卡片字典

    Returns:
        与 run_audit 一致的 checks 字典
    """
    return {
        "checks": {
            "completeness": _check_completeness(card),
            "no_duplicate": _check_no_duplicate(card),
            "anchor_valid": _check_anchor_valid(paper_id, card),
            "hedge_honesty": _check_hedge_honesty(card),
            "author_vs_user": _check_author_vs_user(card),
        }
    }


def backfill_quality_score(limit: int | None = None, dry_run: bool = False):
    """回填 quality_score。

    Args:
        limit: 最多处理多少条记录（None=全部）
        dry_run: 仅打印，不实际更新
    """
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()

        # 查询所有 quality_score 为 NULL 的知识卡片
        sql = """
            SELECT k.paper_id, k.research_question, k.core_answer, k.key_claims,
                   k.evidence_generation, k.boundaries, k.reusable_inspiration,
                   k.source_section_ids, k.quality_score
            FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE COALESCE(p.is_placeholder, 0) = 0
              AND k.quality_score IS NULL
        """
        if limit:
            sql += f" LIMIT {limit}"

        cur.execute(sql)
        cards = [dict(r) for r in cur.fetchall()]

        logger.info(f"找到 {len(cards)} 条 quality_score 为 NULL 的知识卡片")

        updated = 0
        for card in cards:
            paper_id = card["paper_id"]

            # 解析 JSON 字段
            try:
                key_claims = json.loads(card["key_claims"]) if card["key_claims"] else []
            except json.JSONDecodeError:
                key_claims = []

            try:
                boundaries = json.loads(card["boundaries"]) if card["boundaries"] else {}
            except json.JSONDecodeError:
                boundaries = {}

            try:
                reusable_inspiration = json.loads(card["reusable_inspiration"]) if card["reusable_inspiration"] else []
            except json.JSONDecodeError:
                reusable_inspiration = []

            # 构造知识卡片字典
            result = {
                "research_question": card["research_question"] or "",
                "core_answer": card["core_answer"] or "",
                "key_claims": key_claims,
                "evidence_generation": card["evidence_generation"] or "",
                "boundaries": boundaries,
                "reusable_inspiration": reusable_inspiration,
                "source_section_ids": json.loads(card["source_section_ids"]) if card["source_section_ids"] else [],
            }

            # 构造 audit_report 并调用增强版评分器
            audit_report = _build_audit_report(paper_id, result)
            quality_score = evaluate_quality_score(result, audit_report=audit_report)

            if dry_run:
                logger.info(f"[DRY-RUN] paper_id={paper_id} -> quality_score={quality_score:.3f}")
            else:
                conn.execute(
                    "UPDATE paper_knowledge_cards SET quality_score = ? WHERE paper_id = ?",
                    (quality_score, paper_id),
                )
                conn.commit()
                logger.info(f"paper_id={paper_id} quality_score={quality_score:.3f}")

            updated += 1

        logger.info(f"{'[DRY-RUN] ' if dry_run else ''}回填完成：共处理 {updated} 条记录")

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="回填历史知识卡片的 quality_score")
    parser.add_argument("--limit", type=int, default=None, help="最多处理多少条记录")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不实际更新")
    parser.add_argument("--recalibrate", action="store_true",
                        help="重新校准所有非占位论文的 quality_score（覆盖现有分数）")
    args = parser.parse_args()

    if args.recalibrate:
        # 重写：处理所有非占位论文（覆盖现有 quality_score）
        from db import get_connection
        conn = get_connection(init_schema=False, row_factory=True)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT k.paper_id, k.research_question, k.core_answer, k.key_claims,
                       k.evidence_generation, k.boundaries, k.reusable_inspiration,
                       k.source_section_ids, k.quality_score
                FROM paper_knowledge_cards k
                JOIN papers p ON p.id = k.paper_id
                WHERE COALESCE(p.is_placeholder, 0) = 0
            """)
            cards = [dict(r) for r in cur.fetchall()]
            logger.info(f"[RECALIBRATE] 找到 {len(cards)} 条非占位知识卡片")
            updated = 0
            for card in cards:
                paper_id = card["paper_id"]
                try:
                    key_claims = json.loads(card["key_claims"]) if card["key_claims"] else []
                except json.JSONDecodeError:
                    key_claims = []
                try:
                    boundaries = json.loads(card["boundaries"]) if card["boundaries"] else {}
                except json.JSONDecodeError:
                    boundaries = {}
                try:
                    reusable_inspiration = json.loads(card["reusable_inspiration"]) if card["reusable_inspiration"] else []
                except json.JSONDecodeError:
                    reusable_inspiration = []
                result = {
                    "research_question": card["research_question"] or "",
                    "core_answer": card["core_answer"] or "",
                    "key_claims": key_claims,
                    "evidence_generation": card["evidence_generation"] or "",
                    "boundaries": boundaries,
                    "reusable_inspiration": reusable_inspiration,
                    "source_section_ids": json.loads(card["source_section_ids"]) if card["source_section_ids"] else [],
                }
                audit_report = _build_audit_report(paper_id, result)
                quality_score = evaluate_quality_score(result, audit_report=audit_report)
                if args.dry_run:
                    logger.info(f"[DRY-RUN] paper_id={paper_id} {card.get('quality_score')} -> {quality_score:.3f}")
                else:
                    conn.execute(
                        "UPDATE paper_knowledge_cards SET quality_score = ? WHERE paper_id = ?",
                        (quality_score, paper_id),
                    )
                    conn.commit()
                    logger.info(f"paper_id={paper_id} {card.get('quality_score')} -> {quality_score:.3f}")
                updated += 1
            logger.info(f"[RECALIBRATE] 处理完成：共 {updated} 条")
        finally:
            conn.close()
    else:
        backfill_quality_score(limit=args.limit, dry_run=args.dry_run)

