"""批量补全作者 h_index 与 total_citations。

通过 Semantic Scholar /paper/batch 获取作者 ID，再调用 /author/{authorId}
获取 hIndex 与 citationCount，最后更新 authors 表。

用法：
    python scripts/enrich_author_metrics.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "code"))

import config
from db import get_connection
from logger import get_logger

LOGGER = get_logger("enrich_author_metrics")
DB_PATH = ROOT_DIR / "db" / "literature.db"

S2_AUTHOR_URL = "https://api.semanticscholar.org/graph/v1/author/{author_id}"
S2_AUTHOR_FIELDS = "hIndex,citationCount"


def _load_semantic_scholar():
    from sources.semantic_scholar import SemanticScholarAdapter
    return SemanticScholarAdapter()


def _s2_headers():
    headers = {
        "Accept": "application/json",
        "User-Agent": "LiteratureSystem/1.0 (contact: research@example.com; Academic Literature Collection)",
    }
    api_key = config.SEMANTIC_SCHOLAR_API_KEY or ""
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def fetch_author_metrics(author_id: str, timeout: int = 20, retries: int = 3) -> Optional[Dict]:
    """通过 S2 Author API 获取 hIndex 与 citationCount，带指数退避重试。"""
    if not author_id:
        return None
    url = S2_AUTHOR_URL.format(author_id=author_id)
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                params={"fields": S2_AUTHOR_FIELDS},
                headers=_s2_headers(),
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "h_index": data.get("hIndex"),
                    "total_citations": data.get("citationCount"),
                }
            if resp.status_code == 429:
                sleep_time = 2 ** attempt + 0.5
                LOGGER.warning("S2 Author %s 速率限制，%ds 后重试", author_id, sleep_time)
                time.sleep(sleep_time)
                continue
            LOGGER.warning("S2 Author %s 查询失败: HTTP %d", author_id, resp.status_code)
            return None
        except Exception as e:
            LOGGER.warning("S2 Author %s 查询异常: %s", author_id, e)
            time.sleep(1)
    return None


def normalize_name(name: str) -> str:
    """归一化作者名用于匹配。"""
    if not name:
        return ""
    return " ".join(name.lower().split())


def enrich_authors(dry_run: bool = False, batch_size: int = 100) -> Dict:
    conn = get_connection(init_schema=False, row_factory=True, db_path=DB_PATH)
    s2 = _load_semantic_scholar()

    try:
        cur = conn.cursor()
        # 获取所有作者及其论文 DOI
        cur.execute(
            """
            SELECT a.id, a.full_name, p.doi
            FROM authors a
            JOIN paper_authors pa ON pa.author_id = a.id
            JOIN papers p ON p.id = pa.paper_id
            WHERE p.doi IS NOT NULL AND p.doi != ''
            ORDER BY a.id
            """
        )
        author_papers: Dict[int, List[str]] = defaultdict(list)
        author_names: Dict[int, str] = {}
        for row in cur.fetchall():
            aid = row["id"]
            author_names[aid] = row["full_name"]
            author_papers[aid].append(row["doi"])

        # 收集所有 DOI 去重
        all_dois = sorted({d for dois in author_papers.values() for d in dois})
        LOGGER.info("共 %d 位作者，涉及 %d 个唯一 DOI", len(author_names), len(all_dois))

        # 批量查询 S2 论文
        doi_to_authors: Dict[str, List[Dict]] = {}
        for i in range(0, len(all_dois), batch_size):
            batch = all_dois[i : i + batch_size]
            LOGGER.info("批量查询 Semantic Scholar: %d-%d / %d", i + 1, i + len(batch), len(all_dois))
            results = s2.fetch_by_dois_batch(batch, batch_size=batch_size)
            for doi, info in results.items():
                doi_to_authors[doi] = info.get("authors") or []
            time.sleep(0.5)

        # 建立作者名 -> S2 authorId 映射（取出现次数最多的）
        name_to_ids: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for aid, dois in author_papers.items():
            name = normalize_name(author_names.get(aid, ""))
            if not name:
                continue
            for doi in dois:
                s2_authors = doi_to_authors.get(doi, [])
                for sa in s2_authors:
                    s2_name = normalize_name(sa.get("name", ""))
                    s2_id = sa.get("authorId")
                    if s2_id and s2_name and (s2_name == name or name in s2_name or s2_name in name):
                        name_to_ids[name][str(s2_id)] += 1

        # 选择最匹配的 authorId
        author_id_to_db_id: Dict[str, int] = {}
        for aid, name in author_names.items():
            norm = normalize_name(name)
            if norm not in name_to_ids or not name_to_ids[norm]:
                continue
            best_id = max(name_to_ids[norm].items(), key=lambda x: x[1])[0]
            author_id_to_db_id[best_id] = aid

        LOGGER.info("匹配到 %d 位作者的 S2 authorId", len(author_id_to_db_id))

        # 查询作者指标并更新
        to_update: List[Tuple[Optional[int], Optional[int], int]] = []
        errors = 0
        for s2_id, db_id in author_id_to_db_id.items():
            metrics = fetch_author_metrics(s2_id)
            if metrics is None:
                errors += 1
                continue
            h_index = metrics.get("h_index")
            total_citations = metrics.get("total_citations")
            if h_index is not None or total_citations is not None:
                to_update.append((h_index, total_citations, db_id))
            time.sleep(0.35)

        if not dry_run:
            cur.executemany(
                "UPDATE authors SET h_index = ?, total_citations = ? WHERE id = ?",
                to_update,
            )
            conn.commit()
            LOGGER.info("更新作者指标: %d 条", len(to_update))
        else:
            LOGGER.info("[dry-run] 将更新作者指标: %d 条", len(to_update))

        return {
            "total_authors": len(author_names),
            "matched_authors": len(author_id_to_db_id),
            "updated_metrics": len(to_update),
            "errors": errors,
            "dry_run": dry_run,
        }
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="补全作者 h_index 与 total_citations")
    parser.add_argument("--dry-run", action="store_true", help="只输出计划不实际更新")
    parser.add_argument("--batch-size", type=int, default=100, help="Semantic Scholar 批量大小")
    args = parser.parse_args()

    stats = enrich_authors(dry_run=args.dry_run, batch_size=args.batch_size)
    LOGGER.info("统计: %s", stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
