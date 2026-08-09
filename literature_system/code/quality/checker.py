"""
数据质量（DQ）检查脚本 v2

覆盖完整性、唯一性、一致性、有效性四维度：
  - 完整性: 缺失字段（title/abstract/author/doi/journal/published_date 等）
  - 唯一性: DOI 重复、标题重复
  - 一致性: 跨字段逻辑（published_date 与 year 一致、citation_count 非负、
            references_count 与 citations_v2 一致等）
  - 有效性: DOI 格式、日期格式、ORCID 格式、ISSN 格式

输出：
  - dq_issues.csv：按 (doi, 字段, 问题类型, 问题描述) 结构化导出
  - dq_report.json：字段级质量指标 + 总体统计
"""
import re
import json
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict

# 确保独立运行时能找到同级模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from db import get_connection
from logger import get_logger

LOGGER = get_logger("dq_checker")

# ============================================================
# 正则校验
# ============================================================
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[^\s]+$")
ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
ISSN_PATTERN = re.compile(r"^\d{4}-\d{3}[\dX]$")
# ISO 日期：YYYY / YYYY-MM / YYYY-MM-DD
DATE_PATTERN = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


# ============================================================
# 1. 完整性检查
# ============================================================
def check_completeness(conn) -> List[Dict]:
    """检查字段完整性。

    检查字段：title / abstract / author / doi / journal / published_date /
              keywords / language / oa_url
    """
    issues = []
    cur = conn.cursor()

    # 必填字段缺失检查
    required_fields = {
        "title": "缺失标题",
        "abstract": "缺失摘要",
        "doi": "缺失 DOI",
        "published_date": "缺失发表日期",
        "journal": "缺失期刊",
    }
    for field, desc in required_fields.items():
        cur.execute(
            f"SELECT id, doi FROM papers WHERE {field} IS NULL OR {field} = ''"
        )
        for row in cur.fetchall():
            issues.append({
                "paper_id": row["id"],
                "doi": row["doi"],
                "field": field,
                "issue_type": "completeness_missing",
                "issue_desc": desc,
                "severity": "high" if field in ("title", "doi") else "medium",
            })

    # author 字段：JSON 数组长度为 0
    cur.execute(
        """SELECT id, doi, author FROM papers
           WHERE author IS NULL OR json_array_length(author) = 0"""
    )
    for row in cur.fetchall():
        issues.append({
            "paper_id": row["id"],
            "doi": row["doi"],
            "field": "author",
            "issue_type": "completeness_missing",
            "issue_desc": "缺失作者",
            "severity": "high",
        })

    # keywords 缺失
    cur.execute(
        """SELECT id, doi FROM papers
           WHERE keywords IS NULL OR json_array_length(keywords) = 0"""
    )
    for row in cur.fetchall():
        issues.append({
            "paper_id": row["id"],
            "doi": row["doi"],
            "field": "keywords",
            "issue_type": "completeness_missing",
            "issue_desc": "缺失关键词",
            "severity": "low",
        })

    # abstract 过短（< 50 字符，可能为占位）
    cur.execute(
        """SELECT id, doi, length(abstract) AS len FROM papers
           WHERE abstract IS NOT NULL AND length(abstract) < 50"""
    )
    for row in cur.fetchall():
        issues.append({
            "paper_id": row["id"],
            "doi": row["doi"],
            "field": "abstract",
            "issue_type": "completeness_short",
            "issue_desc": f"摘要过短（{row['len']} 字符）",
            "severity": "medium",
        })

    # 有 paper_fulltext 但 abstract 仍空（可用 PDF 补）
    cur.execute(
        """SELECT p.id, p.doi FROM papers p
           JOIN paper_fulltext pf ON p.id = pf.paper_id
           WHERE (p.abstract IS NULL OR p.abstract = '')"""
    )
    for row in cur.fetchall():
        issues.append({
            "paper_id": row["id"],
            "doi": row["doi"],
            "field": "abstract",
            "issue_type": "completeness_missing_but_pdf_available",
            "issue_desc": "摘要缺失但有 PDF 全文可回补",
            "severity": "medium",
        })

    LOGGER.info(f"[completeness] 发现 {len(issues)} 个完整性问题")
    return issues


# ============================================================
# 2. 唯一性检查
# ============================================================
def check_uniqueness(conn) -> List[Dict]:
    """检查唯一性：DOI 重复、标题重复。"""
    issues = []
    cur = conn.cursor()

    # DOI 重复（按理 UNIQUE 约束应阻止，但允许 NULL 多个）
    cur.execute(
        """SELECT doi, COUNT(*) AS c FROM papers
           WHERE doi IS NOT NULL
           GROUP BY doi HAVING c > 1"""
    )
    for row in cur.fetchall():
        # 取所有重复的 paper_id
        cur.execute("SELECT id FROM papers WHERE doi = ?", (row["doi"],))
        for r in cur.fetchall():
            issues.append({
                "paper_id": r["id"],
                "doi": row["doi"],
                "field": "doi",
                "issue_type": "uniqueness_duplicate",
                "issue_desc": f"DOI 重复（共 {row['c']} 条）",
                "severity": "high",
            })

    # 标题重复（可能是同一篇论文被多次入库）
    cur.execute(
        """SELECT LOWER(title) AS norm_title, COUNT(*) AS c, GROUP_CONCAT(id) AS ids
           FROM papers
           WHERE title IS NOT NULL AND length(title) > 20
           GROUP BY norm_title HAVING c > 1"""
    )
    for row in cur.fetchall():
        ids = row["ids"].split(",")
        for pid in ids:
            issues.append({
                "paper_id": int(pid),
                "doi": None,
                "field": "title",
                "issue_type": "uniqueness_duplicate",
                "issue_desc": f"标题重复（共 {row['c']} 条）",
                "severity": "medium",
            })

    LOGGER.info(f"[uniqueness] 发现 {len(issues)} 个唯一性问题")
    return issues


# ============================================================
# 3. 一致性检查
# ============================================================
def check_consistency(conn) -> List[Dict]:
    """检查跨字段一致性。"""
    issues = []
    cur = conn.cursor()

    # published_date 格式与年份一致
    cur.execute("SELECT id, doi, published_date FROM papers WHERE published_date IS NOT NULL")
    for row in cur.fetchall():
        date_str = row["published_date"]
        if not DATE_PATTERN.match(date_str):
            issues.append({
                "paper_id": row["id"],
                "doi": row["doi"],
                "field": "published_date",
                "issue_type": "consistency_invalid_format",
                "issue_desc": f"日期格式异常: {date_str}",
                "severity": "medium",
            })

    # citation_count 负值
    cur.execute(
        "SELECT id, doi, citation_count FROM papers WHERE citation_count < 0"
    )
    for row in cur.fetchall():
        issues.append({
            "paper_id": row["id"],
            "doi": row["doi"],
            "field": "citation_count",
            "issue_type": "consistency_negative",
            "issue_desc": f"引用次数为负: {row['citation_count']}",
            "severity": "high",
        })

    # references_count 与 citations_v2 不一致
    cur.execute(
        """SELECT p.id, p.doi, p.references_count, COUNT(c.id) AS actual_count
           FROM papers p
           LEFT JOIN citations_v2 c ON p.id = c.citing_paper_id
           WHERE p.references_count IS NOT NULL
           GROUP BY p.id
           HAVING p.references_count != COUNT(c.id)"""
    )
    for row in cur.fetchall():
        diff = row["references_count"] - row["actual_count"]
        if abs(diff) > 2:  # 容忍 2 条以内差异
            issues.append({
                "paper_id": row["id"],
                "doi": row["doi"],
                "field": "references_count",
                "issue_type": "consistency_mismatch",
                "issue_desc": f"元数据 {row['references_count']} vs 实际 {row['actual_count']}",
                "severity": "low",
            })

    # 有 paper_fulltext 但无 paper_sections
    cur.execute(
        """SELECT pf.paper_id, p.doi FROM paper_fulltext pf
           JOIN papers p ON p.id = pf.paper_id
           LEFT JOIN paper_sections ps ON ps.paper_id = pf.paper_id
           WHERE ps.id IS NULL"""
    )
    for row in cur.fetchall():
        issues.append({
            "paper_id": row["paper_id"],
            "doi": row["doi"],
            "field": "paper_sections",
            "issue_type": "consistency_missing_section",
            "issue_desc": "有全文但无章节切片",
            "severity": "medium",
        })

    LOGGER.info(f"[consistency] 发现 {len(issues)} 个一致性问题")
    return issues


# ============================================================
# 4. 有效性检查
# ============================================================
def check_validity(conn) -> List[Dict]:
    """检查字段值有效性（DOI 格式、ORCID、ISSN、日期格式）。"""
    issues = []
    cur = conn.cursor()

    # DOI 格式
    cur.execute("SELECT id, doi FROM papers WHERE doi IS NOT NULL")
    for row in cur.fetchall():
        doi = row["doi"]
        if not DOI_PATTERN.match(doi):
            issues.append({
                "paper_id": row["id"],
                "doi": doi,
                "field": "doi",
                "issue_type": "validity_invalid_format",
                "issue_desc": f"DOI 格式非法: {doi}",
                "severity": "high",
            })
        # DOI 大小写不统一（应全小写）
        elif doi != doi.lower():
            issues.append({
                "paper_id": row["id"],
                "doi": doi,
                "field": "doi",
                "issue_type": "validity_case_inconsistent",
                "issue_desc": "DOI 大小写不统一（应小写）",
                "severity": "low",
            })

    # ISSN 格式
    cur.execute("SELECT id, doi, issn FROM papers WHERE issn IS NOT NULL")
    for row in cur.fetchall():
        issn = row["issn"]
        # 可能是 "XXXX-XXXX" 或多个用 ; 分隔
        for one_issn in re.split(r"[;,]", issn):
            one_issn = one_issn.strip()
            if one_issn and not ISSN_PATTERN.match(one_issn):
                issues.append({
                    "paper_id": row["id"],
                    "doi": row["doi"],
                    "field": "issn",
                    "issue_type": "validity_invalid_format",
                    "issue_desc": f"ISSN 格式异常: {one_issn}",
                    "severity": "low",
                })

    # published_date 格式
    cur.execute("SELECT id, doi, published_date FROM papers WHERE published_date IS NOT NULL")
    for row in cur.fetchall():
        date_str = row["published_date"]
        if not DATE_PATTERN.match(date_str):
            issues.append({
                "paper_id": row["id"],
                "doi": row["doi"],
                "field": "published_date",
                "issue_type": "validity_invalid_format",
                "issue_desc": f"日期格式非法: {date_str}",
                "severity": "medium",
            })

    # ORCID 格式（在 author JSON 中）
    cur.execute("SELECT id, doi, author FROM papers WHERE author IS NOT NULL")
    for row in cur.fetchall():
        try:
            authors = json.loads(row["author"]) if isinstance(row["author"], str) else row["author"]
            if isinstance(authors, list):
                for a in authors:
                    if isinstance(a, dict) and a.get("ORCID"):
                        orcid = a["ORCID"]
                        if not ORCID_PATTERN.match(orcid):
                            issues.append({
                                "paper_id": row["id"],
                                "doi": row["doi"],
                                "field": "author.orcid",
                                "issue_type": "validity_invalid_format",
                                "issue_desc": f"ORCID 格式异常: {orcid}",
                                "severity": "low",
                            })
        except (json.JSONDecodeError, TypeError):
            pass

    LOGGER.info(f"[validity] 发现 {len(issues)} 个有效性问题")
    return issues


# ============================================================
# 5. 字段级质量指标
# ============================================================
def compute_field_metrics(conn) -> Dict:
    """计算字段级质量指标。"""
    cur = conn.cursor()
    metrics = {}

    cur.execute("SELECT COUNT(*) AS c FROM papers")
    total = cur.fetchone()["c"]
    metrics["total_papers"] = total

    if total == 0:
        return metrics

    # 各字段完整率
    fields = ["title", "abstract", "doi", "author", "journal", "published_date",
              "keywords", "language", "oa_url", "volume", "issue", "page", "issn"]
    for f in fields:
        cur.execute(
            f"""SELECT COUNT(*) AS c FROM papers
                WHERE {f} IS NOT NULL AND {f} != ''"""
        )
        filled = cur.fetchone()["c"]
        metrics[f"{f}_completeness"] = round(filled / total * 100, 2)

    # author 数组长度 > 0
    cur.execute(
        "SELECT COUNT(*) AS c FROM papers WHERE author IS NOT NULL AND json_array_length(author) > 0"
    )
    metrics["author_nonempty_rate"] = round(cur.fetchone()["c"] / total * 100, 2)

    # DOI 合法率
    cur.execute("SELECT COUNT(*) AS c FROM papers WHERE doi IS NOT NULL")
    has_doi = cur.fetchone()["c"]
    if has_doi > 0:
        cur.execute("SELECT doi FROM papers WHERE doi IS NOT NULL")
        valid_count = sum(1 for r in cur.fetchall() if DOI_PATTERN.match(r["doi"]))
        metrics["doi_valid_rate"] = round(valid_count / has_doi * 100, 2)
    else:
        metrics["doi_valid_rate"] = 0

    # 日期标准化率
    cur.execute("SELECT published_date FROM papers WHERE published_date IS NOT NULL")
    date_rows = cur.fetchall()
    if date_rows:
        valid_dates = sum(1 for r in date_rows if DATE_PATTERN.match(r["published_date"]))
        metrics["date_normalized_rate"] = round(valid_dates / len(date_rows) * 100, 2)
    else:
        metrics["date_normalized_rate"] = 0

    # ORCID 覆盖率
    cur.execute("SELECT author FROM papers WHERE author IS NOT NULL")
    orcid_count = 0
    author_count = 0
    for row in cur.fetchall():
        try:
            authors = json.loads(row["author"]) if isinstance(row["author"], str) else row["author"]
            if isinstance(authors, list):
                author_count += len(authors)
                for a in authors:
                    if isinstance(a, dict) and a.get("ORCID"):
                        orcid_count += 1
        except (json.JSONDecodeError, TypeError):
            pass
    metrics["orcid_coverage"] = round(orcid_count / author_count * 100, 2) if author_count else 0

    # 摘要完整率（>= 50 字符）
    cur.execute(
        "SELECT COUNT(*) AS c FROM papers WHERE abstract IS NOT NULL AND length(abstract) >= 50"
    )
    metrics["abstract_completeness_usable"] = round(cur.fetchone()["c"] / total * 100, 2)

    # PDF 全文覆盖
    cur.execute("SELECT COUNT(DISTINCT paper_id) AS c FROM paper_fulltext")
    metrics["pdf_fulltext_rate"] = round(cur.fetchone()["c"] / total * 100, 2)

    # 章节切片覆盖
    cur.execute("SELECT COUNT(DISTINCT paper_id) AS c FROM paper_sections")
    metrics["sections_rate"] = round(cur.fetchone()["c"] / total * 100, 2)

    # 参考文献覆盖
    cur.execute("SELECT COUNT(DISTINCT citing_paper_id) AS c FROM citations_v2")
    metrics["references_rate"] = round(cur.fetchone()["c"] / total * 100, 2)

    return metrics


# ============================================================
# 主入口
# ============================================================
def run_all_checks(output_dir: Path = None) -> Dict:
    """运行所有 DQ 检查，输出 CSV 与报告。

    Returns:
        {"total_issues": N, "by_dimension": {...}, "metrics": {...},
         "issues_csv": str, "report_path": str}
    """
    if output_dir is None:
        output_dir = config.ROOT_DIR / "db" / "dq_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = get_connection(init_schema=False, row_factory=True)
    try:
        all_issues = []
        all_issues.extend(check_completeness(conn))
        all_issues.extend(check_uniqueness(conn))
        all_issues.extend(check_consistency(conn))
        all_issues.extend(check_validity(conn))

        # 写 CSV
        import csv
        issues_csv = output_dir / "dq_issues.csv"
        with issues_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["paper_id", "doi", "field", "issue_type",
                            "issue_desc", "severity"],
            )
            writer.writeheader()
            for issue in all_issues:
                writer.writerow(issue)

        # 按维度统计
        by_dimension = {
            "completeness": len([i for i in all_issues if i["issue_type"].startswith("completeness")]),
            "uniqueness": len([i for i in all_issues if i["issue_type"].startswith("uniqueness")]),
            "consistency": len([i for i in all_issues if i["issue_type"].startswith("consistency")]),
            "validity": len([i for i in all_issues if i["issue_type"].startswith("validity")]),
        }

        # 字段级指标
        metrics = compute_field_metrics(conn)

        # 写报告
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_papers": metrics.get("total_papers", 0),
            "total_issues": len(all_issues),
            "by_dimension": by_dimension,
            "by_severity": dict(Counter(i["severity"] for i in all_issues)),
            "by_field": dict(Counter(i["field"] for i in all_issues)),
            "field_metrics": metrics,
        }
        report_path = output_dir / "dq_report.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        # 控制台输出
        LOGGER.info("=" * 60)
        LOGGER.info("数据质量检查报告")
        LOGGER.info("=" * 60)
        LOGGER.info(f"总论文数: {metrics.get('total_papers', 0)}")
        LOGGER.info(f"总问题数: {len(all_issues)}")
        LOGGER.info(f"  - 完整性: {by_dimension['completeness']}")
        LOGGER.info(f"  - 唯一性: {by_dimension['uniqueness']}")
        LOGGER.info(f"  - 一致性: {by_dimension['consistency']}")
        LOGGER.info(f"  - 有效性: {by_dimension['validity']}")
        LOGGER.info(f"按严重度: {report['by_severity']}")
        LOGGER.info(f"问题清单: {issues_csv}")
        LOGGER.info(f"质量报告: {report_path}")
        LOGGER.info("-" * 60)
        LOGGER.info("字段级质量指标:")
        for k, v in metrics.items():
            if k != "total_papers":
                LOGGER.info(f"  {k}: {v}%")

        return {
            "total_issues": len(all_issues),
            "by_dimension": by_dimension,
            "metrics": metrics,
            "issues_csv": str(issues_csv),
            "report_path": str(report_path),
        }
    finally:
        conn.close()


def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="数据质量检查 v2")
    parser.add_argument("--output-dir", default=str(config.ROOT_DIR / "db" / "dq_output"), help="输出目录")
    args = parser.parse_args()
    run_all_checks(Path(args.output_dir))


if __name__ == "__main__":
    main()
