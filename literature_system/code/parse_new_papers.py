"""批量解析新采集的论文 PDF"""
import sys
sys.path.insert(0, '.')

import argparse

from db import get_connection
from pdf.scheduler import process_paper
from pdf.downloader import download_pdf_with_fallback
from logger import get_logger

logger = get_logger("parse_new_papers")


def get_new_papers_with_oa(
    limit: int = 20,
    source_prefer: str = "all",
    paper_ids=None,
):
    """获取新采集的、待解析的论文 ID。

    优先选择有 oa_url 的论文；若数量不足，再补充有 DOI 但无 oa_url 的论文，
    通过 DOI 解析策略获取 PDF。

    Args:
        limit: 最多返回的论文数。
        source_prefer: 优先解析的数据源，"all" 表示不限制来源。
    """
    conn = get_connection(init_schema=False, row_factory=True)
    cur = conn.cursor()

    # 查找已解析过的 paper_id
    cur.execute("SELECT DISTINCT paper_id FROM paper_fulltext")
    parsed_ids = {r['paper_id'] for r in cur.fetchall()}

    candidates = []
    source_filter = source_prefer.lower() != "all"

    # 一键流水线传入本次采集的论文 ID，只处理这一批，避免历史积压
    # 任务混入当前进度和结果。
    if paper_ids is not None:
        scoped_ids = [int(paper_id) for paper_id in paper_ids]
        if not scoped_ids:
            conn.close()
            return []
        placeholders = ",".join("?" for _ in scoped_ids)
        params = list(scoped_ids)
        sql = (
            "SELECT id, doi, title, oa_url, source FROM papers "
            f"WHERE id IN ({placeholders})"
        )
        if source_filter:
            sql += " AND source = ?"
            params.append(source_prefer)
        cur.execute(sql, tuple(params))
        rows_by_id = {row["id"]: dict(row) for row in cur.fetchall()}
        candidates = [
            rows_by_id[paper_id]
            for paper_id in scoped_ids
            if paper_id in rows_by_id and paper_id not in parsed_ids
        ][:limit]
        conn.close()
        return candidates

    # 1) 优先：有 oa_url 的论文（可按 source 过滤）
    if source_filter:
        cur.execute("""
            SELECT id, doi, title, oa_url, source
            FROM papers
            WHERE oa_url IS NOT NULL AND oa_url != ''
              AND source = ?
            ORDER BY id DESC
        """, (source_prefer,))
    else:
        cur.execute("""
            SELECT id, doi, title, oa_url, source
            FROM papers
            WHERE oa_url IS NOT NULL AND oa_url != ''
            ORDER BY id DESC
        """)
    for r in cur.fetchall():
        if r['id'] not in parsed_ids:
            candidates.append(dict(r))
            if len(candidates) >= limit:
                conn.close()
                return candidates

    # 2) 兜底：有 DOI 但无 oa_url 的论文（可按 source 过滤）
    if source_filter:
        cur.execute("""
            SELECT id, doi, title, oa_url, source
            FROM papers
            WHERE source = ?
              AND (oa_url IS NULL OR oa_url = '')
              AND doi IS NOT NULL AND doi != ''
            ORDER BY id DESC
        """, (source_prefer,))
    else:
        cur.execute("""
            SELECT id, doi, title, oa_url, source
            FROM papers
            WHERE (oa_url IS NULL OR oa_url = '')
              AND doi IS NOT NULL AND doi != ''
            ORDER BY id DESC
        """)
    for r in cur.fetchall():
        if r['id'] not in parsed_ids:
            candidates.append(dict(r))
            if len(candidates) >= limit:
                break

    conn.close()
    return candidates


def main():
    parser = argparse.ArgumentParser(description="批量解析新采集的论文 PDF")
    parser.add_argument("--source", default="all", help="优先解析的数据源（默认 all，与 UI 采集链路一致）")
    parser.add_argument("--limit", type=int, default=15, help="最多解析篇数（默认 15）")
    parser.add_argument("--force", action="store_true", help="强制重新解析")
    args = parser.parse_args()

    papers = get_new_papers_with_oa(limit=args.limit, source_prefer=args.source)
    print(f"找到 {len(papers)} 篇待解析论文（限制 {args.limit} 篇，来源 {args.source}）")

    success = 0
    failed = 0
    skipped = 0

    for p in papers:
        print(f"\n处理 paper_id={p['id']} [{p['source']}] {p['title'][:60]}...")
        
        # 1. 尝试下载 PDF
        # 优先使用 oa_url（已修复为 PDF 直链）
        pdf_url = p.get('oa_url')
        if not pdf_url and p['doi'] and p['doi'].startswith('oa:'):
            pdf_url = p['doi'][3:]
        
        ok, file_path, err = download_pdf_with_fallback(
            p['doi'] or str(p['id']),
            oa_url=pdf_url,
            timeout=60,
            max_retries=2,
        )
        if not ok:
            print(f"  下载失败: {err}")
            failed += 1
            continue
        if ok:
            print(f"  下载成功: {file_path}")
        
        # 2. 解析 PDF
        try:
            result = process_paper(p['id'], force=args.force)
            status = result.get('status', 'unknown')
            print(f"  状态: {status}, 解析器: {result.get('parser_used')}")
            if status == 'done':
                success += 1
            elif status == 'skipped':
                skipped += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  异常: {e}")
            failed += 1
    
    print(f"\n解析完成: 成功={success}, 跳过={skipped}, 失败={failed}")


if __name__ == "__main__":
    main()
