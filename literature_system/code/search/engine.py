"""
全文检索引擎 v1

基于 SQLite FTS5，提供 Elasticsearch 的常用功能子集：
  - 关键词检索 / 短语检索 / 模糊（前缀）检索
  - 字段过滤（year / journal / author / language / source / doi）
  - BM25 相关性排序与日期排序
  - 检索结果高亮（highlight/snippet）
  - 聚合面板（作者 / 期刊 / 年份 / 语言 / 来源 / 主题）

为什么不直接用 Elasticsearch：
  - 项目数据量小（万级以下）
  - SQLite FTS5 内置于 Python 标准库，无需部署
  - 后续数据规模扩大时可平滑迁移到 ES（SQL 接口契约不变）

数据库结构：
  CREATE VIRTUAL TABLE papers_fts USING fts5(
      paper_id UNINDEXED,
      title, abstract, keywords, authors, journal, full_text,
      published_year UNINDEXED, language UNINDEXED, source UNINDEXED,
      doi UNINDEXED,
      tokenize = 'porter unicode61'
  );

用法：
    from search_engine import SearchEngine
    se = SearchEngine()
    se.rebuild_index()
    result = se.search("livestock grazing", filters={"year_from": 2020})
"""
import re
import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

import config
from logger import get_logger
from db import get_connection

LOGGER = get_logger("search_engine")


# ============================================================
# 索引构建
# ============================================================
def _extract_year(date_str: str) -> Optional[str]:
    if not date_str:
        return None
    m = re.match(r"(\d{4})", date_str)
    return m.group(1) if m else None


def _format_authors(author_json) -> str:
    """把 author JSON 数组转为可索引的字符串。"""
    if not author_json:
        return ""
    try:
        authors = json.loads(author_json) if isinstance(author_json, str) else author_json
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(authors, list):
        return ""
    parts = []
    for a in authors:
        if isinstance(a, dict):
            name = " ".join([a.get("given", ""), a.get("family", "")]).strip()
            if not name:
                name = a.get("name", "")
            if name:
                parts.append(name)
            aff = a.get("affiliation")
            if isinstance(aff, list):
                for x in aff:
                    if isinstance(x, str):
                        parts.append(x)
                    elif isinstance(x, dict):
                        n = x.get("name")
                        if n:
                            parts.append(n)
            elif isinstance(aff, str) and aff:
                parts.append(aff)
    return " ; ".join(parts)


def _format_keywords(kw_json) -> str:
    if not kw_json:
        return ""
    try:
        kw = json.loads(kw_json) if isinstance(kw_json, str) else kw_json
    except (json.JSONDecodeError, TypeError):
        return ""
    if isinstance(kw, list):
        return " ; ".join(str(x) for x in kw if x)
    return str(kw)


# ============================================================
# SearchEngine 主类
# ============================================================
class SearchEngine:
    """基于 SQLite FTS5 的全文检索引擎。"""

    FTS_TABLE = "papers_fts"

    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self._conn = conn

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = get_connection(init_schema=False, row_factory=True)
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------ 索引管理 ------------------
    def ensure_index(self, drop_if_exists: bool = False) -> None:
        """创建 FTS5 虚拟表（如果不存在）。"""
        cur = self.conn.cursor()
        if drop_if_exists:
            cur.execute(f"DROP TABLE IF EXISTS {self.FTS_TABLE}")
        cur.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {self.FTS_TABLE} USING fts5(
                paper_id UNINDEXED,
                title, abstract, keywords, authors, journal, full_text,
                published_year UNINDEXED, language UNINDEXED, source UNINDEXED,
                doi UNINDEXED,
                tokenize = 'porter unicode61'
            )
        """)
        self.conn.commit()

    def rebuild_index(self, progress_callback=None) -> int:
        """重建索引：清空并重新填充。

        Args:
            progress_callback: 可选进度回调，接收 (current, total, message)。
        """
        cur = self.conn.cursor()
        cur.execute(f"DELETE FROM {self.FTS_TABLE}")
        n = self._populate_all(progress_callback=progress_callback)
        self.conn.commit()
        LOGGER.info(f"重建索引完成，共 {n} 篇论文")
        return n

    def _populate_all(self, progress_callback=None) -> int:
        cur = self.conn.cursor()
        # 排除占位论文（is_placeholder=1）
        cur.execute("""
            SELECT p.id, p.title, p.abstract, p.keywords, p.author,
                   p.journal, p.published_date, p.language, p.source, p.doi,
                   (SELECT full_text FROM paper_fulltext pf WHERE pf.paper_id = p.id) AS full_text
            FROM papers p
            WHERE (p.title IS NOT NULL OR p.abstract IS NOT NULL)
              AND COALESCE(p.is_placeholder, 0) = 0
        """)
        rows = cur.fetchall()
        total = len(rows)
        n = 0
        for r in rows:
            self._upsert_row(r)
            n += 1
            if progress_callback and total > 0:
                progress_callback(n, total)
        return n

    def _upsert_row(self, row: sqlite3.Row) -> None:
        """插入或更新单条到 FTS 表。"""
        cur = self.conn.cursor()
        # 先删除旧记录
        cur.execute(f"DELETE FROM {self.FTS_TABLE} WHERE paper_id = ?", (row["id"],))
        cur.execute(f"""
            INSERT INTO {self.FTS_TABLE}
                (paper_id, title, abstract, keywords, authors, journal, full_text,
                 published_year, language, source, doi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["id"],
            row["title"] or "",
            row["abstract"] or "",
            _format_keywords(row["keywords"]),
            _format_authors(row["author"]),
            row["journal"] or "",
            row["full_text"] or "",
            _extract_year(row["published_date"]) or "",
            row["language"] or "",
            row["source"] or "",
            row["doi"] or "",
        ))

    def sync_paper(self, paper_id: int) -> bool:
        """同步单篇论文（增量更新）。

        如果论文为占位论文（is_placeholder=1），则从索引中删除。
        """
        cur = self.conn.cursor()
        # 检查是否为占位论文
        cur.execute("SELECT is_placeholder FROM papers WHERE id = ?", (paper_id,))
        paper_row = cur.fetchone()
        if paper_row and (paper_row["is_placeholder"] if isinstance(paper_row, sqlite3.Row) else paper_row.get("is_placeholder")) == 1:
            # 占位论文，从索引中删除
            cur.execute(f"DELETE FROM {self.FTS_TABLE} WHERE paper_id = ?", (paper_id,))
            self.conn.commit()
            LOGGER.info("paper_id=%d 为占位论文，已从索引中删除", paper_id)
            return False

        cur.execute("""
            SELECT p.id, p.title, p.abstract, p.keywords, p.author,
                   p.journal, p.published_date, p.language, p.source, p.doi,
                   (SELECT full_text FROM paper_fulltext pf WHERE pf.paper_id = p.id) AS full_text
            FROM papers p WHERE p.id = ?
        """, (paper_id,))
        row = cur.fetchone()
        if not row:
            return False
        self._upsert_row(row)
        self.conn.commit()
        return True

    # ------------------ 检索 ------------------
    @staticmethod
    def _build_match(query: str, mode: str, fields: Optional[List[str]]) -> str:
        """构造 FTS5 MATCH 表达式。"""
        # 转义双引号
        q = query.replace('"', '""')

        if mode == "phrase":
            # 短语检索：整个查询作为一个短语
            match = f'"{q}"'
        elif mode == "fuzzy":
            # 模糊检索：每个 token 加前缀 *
            tokens = [t for t in re.split(r"\s+", q) if t]
            match = " ".join(f"{t}*" for t in tokens)
        else:
            # 默认 keyword：按空格切分为 AND
            tokens = [t for t in re.split(r"\s+", q) if t]
            match = " ".join(tokens)

        if fields:
            # 字段限定：{field1}: query OR {field2}: query ...
            # FTS5 字段限定语法：field:match
            ors = " OR ".join(f"{f} : {match}" for f in fields if f)
            return ors or match
        return match

    def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        mode: str = "keyword",
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "relevance",
        highlight: bool = True,
        snippet_size: int = 5,
    ) -> Dict:
        """执行检索。

        Args:
            query: 检索字符串
            fields: 限定检索字段（如 ['title','abstract']）
            filters: 过滤条件 dict，支持
                - year_from / year_to (int)
                - year (str, 精确匹配年份)
                - journal (str, 子串)
                - author (str, 子串)
                - language (str)
                - source (str)
                - doi (str, 子串)
            mode: keyword / phrase / fuzzy
            limit / offset: 分页
            sort_by: relevance / date_desc / date_asc
            highlight: 是否返回高亮片段
            snippet_size: snippet 周围 token 数

        Returns:
            {
                "total": int,
                "hits": [{paper_id, doi, title, abstract_snippet, score, published_date, journal, ...}],
                "aggregations": {...},
                "query": {"q": ..., "mode": ..., "filters": ...},
            }
        """
        filters = filters or {}
        # 兼容 journal_tier（单值） / journal_tiers（多值，列表/集合/逗号串）
        tier_values: List[str] = []
        if filters.get("journal_tiers"):
            v = filters["journal_tiers"]
            if isinstance(v, (list, tuple, set)):
                tier_values = [str(x) for x in v if x]
            elif isinstance(v, str):
                tier_values = [t.strip() for t in v.split(",") if t.strip()]
        elif filters.get("journal_tier"):
            tier_values = [str(filters["journal_tier"])]
        match_expr = self._build_match(query, mode, fields) if query and query.strip() else None

        where_parts = []
        params: List[Any] = []

        if match_expr:
            where_parts.append(f"{self.FTS_TABLE} MATCH ?")
            params.append(match_expr)

        # 字段过滤
        if filters.get("year_from"):
            where_parts.append("fts.published_year >= ?")
            params.append(str(filters["year_from"]))
        if filters.get("year_to"):
            where_parts.append("fts.published_year <= ?")
            params.append(str(filters["year_to"]))
        if filters.get("year"):
            where_parts.append("fts.published_year = ?")
            params.append(str(filters["year"]))
        if filters.get("journal"):
            where_parts.append("fts.journal LIKE ?")
            params.append(f"%{filters['journal']}%")
        if filters.get("author"):
            where_parts.append("fts.authors LIKE ?")
            params.append(f"%{filters['author']}%")
        if filters.get("language"):
            where_parts.append("fts.language = ?")
            params.append(filters["language"])
        if filters.get("source"):
            where_parts.append("fts.source = ?")
            params.append(filters["source"])
        if filters.get("doi"):
            where_parts.append("fts.doi LIKE ?")
            params.append(f"%{filters['doi']}%")
        # 期刊分级（多值）：通过子查询过滤 papers.journal_tier
        if tier_values:
            placeholders = ",".join("?" for _ in tier_values)
            where_parts.append(
                f"fts.paper_id IN (SELECT id FROM papers WHERE journal_tier IN ({placeholders}))"
            )
            params.extend(tier_values)

        where_clause = " WHERE " + " AND ".join(where_parts) if where_parts else ""

        # 排序
        if sort_by == "date_desc":
            order = "published_year DESC, bm25(%s) ASC" % self.FTS_TABLE
        elif sort_by == "date_asc":
            order = "published_year ASC, bm25(%s) ASC" % self.FTS_TABLE
        else:  # relevance
            order = "bm25(%s) ASC" % self.FTS_TABLE  # 注意 bm25 越小越相关

        # 引入别名 fts 以便子查询引用 papers.journal_tier
        from_joins = f"{self.FTS_TABLE} AS fts"
        # 注意：where_clause 内的 MATCH 子句必须使用原表名 {self.FTS_TABLE}，
        # 其它列（paper_id, published_year 等）已显式使用 fts. 前缀，可被正常解析。

        # 主查询
        select_cols = ["fts.paper_id", "fts.doi", "fts.title", "fts.journal", "fts.published_year",
                       "fts.language", "fts.source", "fts.authors", "fts.keywords"]

        if highlight and match_expr:
            # title=1, abstract=2, full_text=6 (按建表顺序索引，UNINDEXED 也计数)
            highlight_title = f"highlight({self.FTS_TABLE}, 1, '<em>', '</em>') AS title_hl"
            highlight_abs = f"snippet({self.FTS_TABLE}, 2, '<em>', '</em>', ' ... ', {snippet_size}) AS abstract_hl"
            select_cols.extend([highlight_title, highlight_abs])
        else:
            select_cols.extend(["fts.title AS title_hl", "fts.abstract AS abstract_hl"])

        # 期刊分级（关联 papers 表取 journal_tier 字段）
        select_cols.append(
            "(SELECT journal_tier FROM papers WHERE id = fts.paper_id) AS journal_tier"
        )

        select_clause = ", ".join(select_cols)
        # bm25() / highlight() / snippet() 等 FTS5 辅助函数必须用原始虚拟表名，不能用别名
        sql = f"""
            SELECT {select_clause}, bm25({self.FTS_TABLE}) AS score
            FROM {from_joins}{where_clause}
            ORDER BY {order}
            LIMIT ? OFFSET ?
        """
        cur = self.conn.cursor()
        cur.execute(sql, params + [limit, offset])
        hits = []
        for row in cur.fetchall():
            hits.append({
                "paper_id": row["paper_id"],
                "doi": row["doi"],
                "title": row["title_hl"] or row["title"],
                "abstract_snippet": row["abstract_hl"],
                "journal": row["journal"],
                "published_year": row["published_year"],
                "language": row["language"],
                "source": row["source"],
                "authors": row["authors"],
                "keywords": row["keywords"],
                "journal_tier": row["journal_tier"],
                "score": round(row["score"], 4),
            })

        # 计数
        count_sql = f"SELECT COUNT(*) AS c FROM {from_joins}{where_clause}"
        cur.execute(count_sql, params)
        total = cur.fetchone()["c"]

        # 聚合
        aggregations = {}
        if match_expr or filters:
            aggregations = self._aggregate_internal(where_clause, params)

        return {
            "total": total,
            "hits": hits,
            "aggregations": aggregations,
            "query": {"q": query, "mode": mode, "filters": filters,
                      "fields": fields, "sort_by": sort_by,
                      "limit": limit, "offset": offset},
        }

    def _aggregate_internal(self, where_clause: str, params: list) -> Dict:
        """对当前结果集做聚合。

        where_clause 形如 " WHERE cond1 AND cond2" 或空字符串。
        额外条件用 _and() 包装。
        注意：SQLite FTS5 的 MATCH 左操作数必须使用虚拟表原名，
        不能使用 FROM 子句别名。
        """
        agg = {}
        cur = self.conn.cursor()
        fts_alias = f"{self.FTS_TABLE} fts"

        def _and(extra: str) -> str:
            """把额外条件拼到现有 where_clause 上。"""
            if not extra:
                return where_clause
            if where_clause:
                return where_clause + " AND " + extra
            return " WHERE " + extra

        # 期刊分级（聚合面板）—— 只对当前 where 已过滤的 paper_id 子集统计
        cur.execute(f"""
            SELECT p.journal_tier AS k, COUNT(*) AS c
            FROM {fts_alias}
            JOIN papers p ON p.id = fts.paper_id{where_clause}
            GROUP BY p.journal_tier
            ORDER BY c DESC
        """, params)
        tier_labels = {"tier1": "T1", "tier2": "T2", "tier3": "T3", "other": "其他"}
        agg["journal_tier"] = [
            {"key": (r["k"] or "unknown"), "label": tier_labels.get(r["k"], r["k"] or "未分级"),
             "count": r["c"]}
            for r in cur.fetchall()
        ]

        # 年份
        cur.execute(f"""
            SELECT published_year AS k, COUNT(*) AS c
            FROM {fts_alias}{where_clause}
            GROUP BY published_year ORDER BY k DESC
        """, params)
        agg["year"] = [{"key": r["k"] or "unknown", "count": r["c"]} for r in cur.fetchall()]

        # 期刊
        cur.execute(f"""
            SELECT journal AS k, COUNT(*) AS c
            FROM {fts_alias}{_and("fts.journal != ''")}
            GROUP BY journal ORDER BY c DESC LIMIT 20
        """, params)
        agg["journal"] = [{"key": r["k"], "count": r["c"]} for r in cur.fetchall()]

        # 语言
        cur.execute(f"""
            SELECT language AS k, COUNT(*) AS c
            FROM {fts_alias}{where_clause}
            GROUP BY language ORDER BY c DESC
        """, params)
        agg["language"] = [{"key": r["k"] or "unknown", "count": r["c"]} for r in cur.fetchall()]

        # 来源
        cur.execute(f"""
            SELECT source AS k, COUNT(*) AS c
            FROM {fts_alias}{where_clause}
            GROUP BY source ORDER BY c DESC
        """, params)
        agg["source"] = [{"key": r["k"] or "unknown", "count": r["c"]} for r in cur.fetchall()]

        # 作者 Top N（需要拆分 authors 字段）
        cur.execute(f"""
            SELECT authors AS k
            FROM {fts_alias}{_and("fts.authors != ''")}
        """, params)
        author_counter = defaultdict(int)
        for r in cur.fetchall():
            for name in (r["k"] or "").split(";"):
                name = name.strip()
                if name:
                    author_counter[name] += 1
        agg["author"] = [{"key": k, "count": v} for k, v in
                        sorted(author_counter.items(), key=lambda x: -x[1])[:20]]

        # 关键词 Top N
        cur.execute(f"""
            SELECT keywords AS k
            FROM {fts_alias}{_and("fts.keywords != ''")}
        """, params)
        kw_counter = defaultdict(int)
        for r in cur.fetchall():
            for kw in (r["k"] or "").split(";"):
                kw = kw.strip()
                if kw:
                    kw_counter[kw.lower()] += 1
        agg["keyword"] = [{"key": k, "count": v} for k, v in
                         sorted(kw_counter.items(), key=lambda x: -x[1])[:20]]

        return agg

    def aggregate(self, query: str = "*", filters: Optional[Dict] = None,
                  mode: str = "keyword") -> Dict:
        """只做聚合，不返回 hits。"""
        filters = filters or {}
        # 兼容 journal_tier（单值） / journal_tiers（多值，列表/集合/逗号串）
        tier_values: List[str] = []
        if filters.get("journal_tiers"):
            v = filters["journal_tiers"]
            if isinstance(v, (list, tuple, set)):
                tier_values = [str(x) for x in v if x]
            elif isinstance(v, str):
                tier_values = [t.strip() for t in v.split(",") if t.strip()]
        elif filters.get("journal_tier"):
            tier_values = [str(filters["journal_tier"])]
        match_expr = self._build_match(query, mode, None) if query and query.strip() != "*" else None
        where_parts = []
        params = []
        if match_expr:
            where_parts.append(f"{self.FTS_TABLE} MATCH ?")
            params.append(match_expr)
        if tier_values:
            placeholders = ",".join("?" for _ in tier_values)
            where_parts.append(
                f"fts.paper_id IN (SELECT id FROM papers WHERE journal_tier IN ({placeholders}))"
            )
            params.extend(tier_values)
        where_clause = " WHERE " + " AND ".join(where_parts) if where_parts else ""
        return self._aggregate_internal(where_clause, params)

    # ------------------ 详情 ------------------
    def get_paper_detail(self, paper_id: int) -> Optional[Dict]:
        """获取论文详情（含 sections / figures / references 等）。"""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
        row = cur.fetchone()
        if not row:
            return None

        paper = dict(row)
        # 解析 JSON 字段
        for k in ("author", "keywords", "external_ids", "meta_json"):
            if paper.get(k):
                try:
                    paper[k] = json.loads(paper[k]) if isinstance(paper[k], str) else paper[k]
                except (json.JSONDecodeError, TypeError):
                    pass

        # 章节
        cur.execute("""
            SELECT section_type, heading, content, page_start, page_end, order_idx
            FROM paper_sections WHERE paper_id = ?
            ORDER BY order_idx
        """, (paper_id,))
        paper["sections"] = [dict(r) for r in cur.fetchall()]

        # 图表
        cur.execute("""
            SELECT fig_label, fig_type, caption, file_path, page
            FROM paper_figures WHERE paper_id = ?
            ORDER BY id
        """, (paper_id,))
        paper["figures"] = [dict(r) for r in cur.fetchall()]

        # 引用
        cur.execute("""
            SELECT cited_doi, cited_title, cited_authors, cited_year, raw_reference,
                   match_method, match_confidence
            FROM citations_v2 WHERE citing_paper_id = ?
            ORDER BY id
        """, (paper_id,))
        paper["references"] = [dict(r) for r in cur.fetchall()]

        # 全文摘要
        cur.execute("""
            SELECT parser_used, parse_quality, char_count, page_count, parsed_at
            FROM paper_fulltext WHERE paper_id = ?
        """, (paper_id,))
        pf = cur.fetchone()
        paper["fulltext_meta"] = dict(pf) if pf else None

        # 资助者
        cur.execute("""
            SELECT f.name, f.doi, f.award
            FROM paper_funders pf
            JOIN funders f ON f.id = pf.funder_id
            WHERE pf.paper_id = ?
        """, (paper_id,))
        paper["funders"] = [dict(r) for r in cur.fetchall()]

        return paper


# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="全文检索引擎 (SQLite FTS5)")
    sub = parser.add_subparsers(dest="cmd")

    p_rebuild = sub.add_parser("rebuild", help="重建索引")
    p_rebuild.add_argument("--drop", action="store_true", help="先删除再重建")

    p_sync = sub.add_parser("sync", help="同步单篇论文")
    p_sync.add_argument("paper_id", type=int)

    p_search = sub.add_parser("search", help="检索")
    p_search.add_argument("query", help="检索词")
    p_search.add_argument("--mode", choices=["keyword", "phrase", "fuzzy"], default="keyword")
    p_search.add_argument("--fields", help="限定字段（逗号分隔）")
    p_search.add_argument("--year-from", type=int)
    p_search.add_argument("--year-to", type=int)
    p_search.add_argument("--year")
    p_search.add_argument("--journal")
    p_search.add_argument("--author")
    p_search.add_argument("--language")
    p_search.add_argument("--source")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--offset", type=int, default=0)
    p_search.add_argument("--sort", choices=["relevance", "date_desc", "date_asc"], default="relevance")
    p_search.add_argument("--no-highlight", action="store_true")
    p_search.add_argument("--no-agg", action="store_true", help="不返回聚合")

    p_agg = sub.add_parser("aggregate", help="仅聚合")
    p_agg.add_argument("query", nargs="?", default="*")
    p_agg.add_argument("--mode", choices=["keyword", "phrase", "fuzzy"], default="keyword")

    p_detail = sub.add_parser("detail", help="论文详情")
    p_detail.add_argument("paper_id", type=int)

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        return

    se = SearchEngine()
    try:
        if args.cmd == "rebuild":
            se.ensure_index(drop_if_exists=args.drop)
            n = se.rebuild_index()
            print(f"已重建索引：{n} 篇论文")

        elif args.cmd == "sync":
            se.ensure_index()
            ok = se.sync_paper(args.paper_id)
            print(f"同步论文 {args.paper_id}: {'成功' if ok else '失败'}")

        elif args.cmd == "search":
            se.ensure_index()
            filters = {}
            for k, v in [("year_from", args.year_from), ("year_to", args.year_to),
                         ("year", args.year), ("journal", args.journal),
                         ("author", args.author), ("language", args.language),
                         ("source", args.source)]:
                if v is not None and v != "":
                    filters[k] = v
            fields = args.fields.split(",") if args.fields else None

            result = se.search(
                args.query, fields=fields, filters=filters, mode=args.mode,
                limit=args.limit, offset=args.offset, sort_by=args.sort,
                highlight=not args.no_highlight,
            )

            print(f"\n=== 检索结果（共 {result['total']} 条，返回 {len(result['hits'])} 条）===")
            for i, hit in enumerate(result["hits"], 1):
                print(f"\n[{i}] (score={hit['score']}) {hit['title']}")
                if hit.get("doi"):
                    print(f"    DOI: {hit['doi']}")
                if hit.get("abstract_snippet"):
                    print(f"    摘要: {hit['abstract_snippet']}")
                if hit.get("journal"):
                    print(f"    期刊: {hit['journal']}")
                if hit.get("published_year"):
                    print(f"    年份: {hit['published_year']}")
                if hit.get("authors"):
                    print(f"    作者: {hit['authors'][:100]}")

            if not args.no_agg and result.get("aggregations"):
                print("\n=== 聚合面板 ===")
                for facet, items in result["aggregations"].items():
                    if items:
                        print(f"\n[{facet}]")
                        for it in items[:5]:
                            print(f"  {it['key']}: {it['count']}")

        elif args.cmd == "aggregate":
            se.ensure_index()
            agg = se.aggregate(args.query, mode=args.mode)
            print(json.dumps(agg, indent=2, ensure_ascii=False))

        elif args.cmd == "detail":
            paper = se.get_paper_detail(args.paper_id)
            if not paper:
                print("论文不存在")
            else:
                print(json.dumps(paper, indent=2, ensure_ascii=False, default=str))

    finally:
        se.close()


if __name__ == "__main__":
    main()
