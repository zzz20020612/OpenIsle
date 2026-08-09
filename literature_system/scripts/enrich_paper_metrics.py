"""批量补全论文 citation_count 与关键词。

使用 Semantic Scholar /paper/batch 查询 DOI，获取 citationCount 与 fieldsOfStudy；
对缺失 keywords 的论文，额外尝试 Crossref 反查 subject 字段作为关键词补充。

用法：
    python scripts/enrich_paper_metrics.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

# 确保项目根目录在路径中
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "code"))

import config
from db import get_connection
from logger import get_logger

LOGGER = get_logger("enrich_paper_metrics")
DB_PATH = ROOT_DIR / "db" / "literature.db"

# Crossref 礼貌池
CROSSREF_BASE = "https://api.crossref.org/works"
MAILTO = getattr(config, "CROSSREF_MAILTO", "") or "research@example.com"
UA = {"User-Agent": f"literature-system/0.1 (mailto:{MAILTO})"}


def _load_semantic_scholar():
    from sources.semantic_scholar import SemanticScholarAdapter
    return SemanticScholarAdapter()


def fetch_crossref_subjects(doi: str, timeout: int = 20) -> Optional[List[str]]:
    """通过 DOI 反查 Crossref 获取 subject 作为关键词补充。"""
    import requests
    try:
        url = f"{CROSSREF_BASE}/{doi}"
        r = requests.get(url, headers=UA, timeout=timeout)
        if r.status_code != 200:
            return None
        msg = r.json().get("message", {})
        subjects = msg.get("subject") or []
        # 有时 subject 是字符串，有时是列表
        if isinstance(subjects, str):
            subjects = [subjects]
        return [s.strip() for s in subjects if s and isinstance(s, str)]
    except Exception as e:
        LOGGER.warning("Crossref 查询 %s 失败: %s", doi, e)
        return None


def normalize_subjects(subjects: List[str]) -> List[str]:
    """清洗并去重 subject 列表。"""
    seen: Set[str] = set()
    result: List[str] = []
    for s in subjects:
        s = re.sub(r"\s+", " ", s).strip()
        if not s:
            continue
        key = s.lower()
        if key not in seen:
            seen.add(key)
            result.append(s)
    return result


def enrich_papers(dry_run: bool = False, batch_size: int = 100) -> Dict:
    conn = get_connection(init_schema=False, row_factory=True, db_path=DB_PATH)
    s2 = _load_semantic_scholar()

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, doi, title, citation_count, keywords
            FROM papers
            WHERE doi IS NOT NULL AND doi != ''
            ORDER BY id
            """
        )
        papers = [dict(r) for r in cur.fetchall()]

        to_update_citation: List[tuple] = []
        to_update_keywords: List[tuple] = []
        s2_hits = 0
        crossref_hits = 0

        for i in range(0, len(papers), batch_size):
            batch = papers[i : i + batch_size]
            dois = [p["doi"] for p in batch]
            LOGGER.info("批量查询 Semantic Scholar: %d-%d / %d", i + 1, i + len(batch), len(papers))
            results = s2.fetch_by_dois_batch(dois, batch_size=batch_size)

            for p in batch:
                doi = p["doi"]
                info = results.get(doi.lower())
                if not info:
                    continue
                s2_hits += 1

                # citation_count
                cc = info.get("citation_count")
                if cc is not None and (p["citation_count"] is None or p["citation_count"] == ""):
                    to_update_citation.append((int(cc), p["id"]))

                # keywords：优先用已有，缺失时尝试 fieldsOfStudy 或 Crossref subjects
                existing = p["keywords"]
                existing_list: List[str] = []
                if existing:
                    try:
                        parsed = json.loads(existing) if isinstance(existing, str) else existing
                        if isinstance(parsed, list):
                            existing_list = [str(x) for x in parsed if x]
                    except json.JSONDecodeError:
                        existing_list = [x.strip() for x in re.split(r"[,;]", existing) if x.strip()]

                if not existing_list:
                    candidates: List[str] = []
                    fos = info.get("fields_of_study") or []
                    if fos:
                        candidates.extend(fos)
                    if not candidates:
                        subjects = fetch_crossref_subjects(doi)
                        if subjects:
                            candidates.extend(subjects)
                            crossref_hits += 1
                    if candidates:
                        normalized = normalize_subjects(candidates)
                        to_update_keywords.append((json.dumps(normalized, ensure_ascii=False), p["id"]))

            # 礼貌延迟
            time.sleep(0.5)

        # 执行更新
        if not dry_run:
            if to_update_citation:
                cur.executemany(
                    "UPDATE papers SET citation_count = ? WHERE id = ?",
                    to_update_citation,
                )
                LOGGER.info("更新 citation_count: %d 条", len(to_update_citation))
            if to_update_keywords:
                cur.executemany(
                    "UPDATE papers SET keywords = ? WHERE id = ?",
                    to_update_keywords,
                )
                LOGGER.info("更新 keywords: %d 条", len(to_update_keywords))
            conn.commit()
        else:
            LOGGER.info("[dry-run] 将更新 citation_count: %d 条, keywords: %d 条", len(to_update_citation), len(to_update_keywords))

        return {
            "total_papers": len(papers),
            "s2_hits": s2_hits,
            "crossref_hits": crossref_hits,
            "updated_citation_count": len(to_update_citation),
            "updated_keywords": len(to_update_keywords),
            "dry_run": dry_run,
        }
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="补全论文 citation_count 与 keywords")
    parser.add_argument("--dry-run", action="store_true", help="只输出计划不实际更新")
    parser.add_argument("--batch-size", type=int, default=100, help="Semantic Scholar 批量大小")
    args = parser.parse_args()

    stats = enrich_papers(dry_run=args.dry_run, batch_size=args.batch_size)
    LOGGER.info("统计: %s", stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
