"""从 papers.author 字段解析并填充 authors / paper_authors 表。

用法:
    python scripts/populate_authors.py
    python scripts/populate_authors.py --paper-id 123
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from db import get_connection
from search.institution_normalizer import normalize_affiliations, normalize_institution_name


def parse_affiliation_value(aff):
    """将原始机构字段解析为字符串。"""
    if isinstance(aff, dict):
        return aff.get("name") or aff.get("text") or ""
    if isinstance(aff, str):
        return aff.strip()
    return ""


def parse_author_list(author_str):
    """解析 papers.author 字段，返回结构化作者列表。"""
    if not author_str or not str(author_str).strip():
        return []

    author_str = str(author_str).strip()

    # 尝试 JSON 列表解析（Crossref / OpenAlex 格式）
    try:
        data = json.loads(author_str)
        if isinstance(data, list):
            authors = []
            for a in data:
                if not isinstance(a, dict):
                    continue
                given = (a.get("given") or "").strip()
                family = (a.get("family") or "").strip()
                orcid = a.get("orcid") or a.get("ORCID") or None
                if orcid:
                    orcid = str(orcid).strip()
                affs = a.get("affiliation", [])
                if isinstance(affs, list):
                    raw_names = [
                        parse_affiliation_value(x)
                        for x in affs
                        if parse_affiliation_value(x)
                    ]
                    aff_names = normalize_affiliations(raw_names)
                else:
                    aff_names = []
                full = f"{given} {family}".strip()
                if not full:
                    full = a.get("name", "").strip()
                authors.append({
                    "given_name": given,
                    "family_name": family,
                    "full_name": full,
                    "orcid": orcid,
                    "affiliation": aff_names,
                })
            return authors
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback：纯字符串，按逗号分隔
    authors = []
    for part in author_str.split(","):
        part = part.strip()
        if not part:
            continue
        words = part.split()
        if len(words) > 1:
            given = " ".join(words[:-1])
            family = words[-1]
        else:
            given = ""
            family = words[0] if words else ""
        authors.append({
            "given_name": given,
            "family_name": family,
            "full_name": part,
            "orcid": None,
            "affiliation": [],
        })
    return authors


def make_author_key(author):
    """生成去重 key：优先 ORCID，否则全名小写。"""
    if author.get("orcid"):
        return ("orcid", author["orcid"].strip())
    return ("name", author.get("full_name", "").strip().lower())


def _load_author_id_map(cur):
    """加载 authors 表的 key -> id 映射。"""
    cur.execute("SELECT id, orcid, full_name FROM authors")
    author_id_map = {}
    for row in cur.fetchall():
        author_id, orcid, full_name = row
        if orcid:
            author_id_map[("orcid", orcid.strip())] = author_id
        if full_name:
            author_id_map[("name", full_name.strip().lower())] = author_id
    return author_id_map


def _insert_or_update_authors(cur, authors):
    """将作者列表写入 authors 表，返回新增/跳过计数。"""
    inserted = 0
    skipped = 0
    for a in authors:
        try:
            cur.execute(
                """INSERT OR IGNORE INTO authors
                   (orcid, given_name, family_name, full_name, affiliation,
                    current_affiliation, total_publications, meta_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    a.get("orcid"),
                    a.get("given_name"),
                    a.get("family_name"),
                    a.get("full_name"),
                    json.dumps(a.get("affiliation", []), ensure_ascii=False),
                    normalize_institution_name(a.get("affiliation", [None])[0]) if a.get("affiliation") else None,
                    0,
                    json.dumps({"parsed_from": "papers.author"}, ensure_ascii=False),
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"插入作者失败 {a}: {e}")
            skipped += 1
    return inserted, skipped


def _link_paper_authors(cur, paper_id, authors, author_id_map):
    """建立 paper_authors 关联，返回新增/跳过计数。"""
    pa_inserted = 0
    pa_skipped = 0
    for order, a in enumerate(authors, start=1):
        key = make_author_key(a)
        author_id = author_id_map.get(key)
        if not author_id:
            pa_skipped += 1
            continue
        try:
            cur.execute(
                """INSERT OR IGNORE INTO paper_authors
                   (paper_id, author_id, author_order, is_corresponding)
                   VALUES (?, ?, ?, ?)""",
                (paper_id, author_id, order, 0),
            )
            if cur.rowcount > 0:
                pa_inserted += 1
        except Exception as e:
            print(f"插入 paper_authors 失败 {paper_id}-{author_id}: {e}")
            pa_skipped += 1
    return pa_inserted, pa_skipped


def _update_total_publications(cur):
    cur.execute("""
        UPDATE authors
        SET total_publications = (
            SELECT COUNT(*) FROM paper_authors WHERE paper_authors.author_id = authors.id
        )
    """)


def populate(paper_id=None, normalize_existing: bool = True):
    """解析 papers.author 并填充 authors / paper_authors 表。

    Args:
        paper_id: 仅处理指定论文；None 时处理全部论文。
        normalize_existing: 是否对 authors 表中已有机构字段执行归一化。
            单篇调用时设为 False 以避免重复全局扫描；全量修复时再设为 True。
    """
    conn = get_connection(init_schema=False, row_factory=False)
    cur = conn.cursor()

    if paper_id is not None:
        cur.execute(
            "SELECT id, author FROM papers WHERE id = ? AND author IS NOT NULL AND author != ''",
            (paper_id,),
        )
    else:
        cur.execute("SELECT id, author FROM papers WHERE author IS NOT NULL AND author != ''")
    rows = cur.fetchall()

    author_cache = {}

    # 收集去重作者
    for pid, author_str in rows:
        authors = parse_author_list(author_str)
        for a in authors:
            key = make_author_key(a)
            if key not in author_cache:
                author_cache[key] = a

    if not author_cache:
        print("未解析到任何作者")
        conn.close()
        return

    scope = f"论文 {paper_id}" if paper_id is not None else f"{len(rows)} 篇论文"
    print(f"解析到 {len(author_cache)} 位唯一作者（{scope}）")

    inserted, skipped = _insert_or_update_authors(cur, author_cache.values())
    conn.commit()
    print(f"authors 表：新增 {inserted}，跳过/已存在 {skipped}")

    # 建立 memory 映射：key -> author_id
    author_id_map = _load_author_id_map(cur)

    # 填充 paper_authors
    pa_inserted = 0
    pa_skipped = 0
    for pid, author_str in rows:
        authors = parse_author_list(author_str)
        pi, ps = _link_paper_authors(cur, pid, authors, author_id_map)
        pa_inserted += pi
        pa_skipped += ps

    conn.commit()
    print(f"paper_authors 表：新增 {pa_inserted}，失败/已存在 {pa_skipped}")

    # 更新 total_publications 统计
    _update_total_publications(cur)
    conn.commit()

    if normalize_existing:
        normalize_existing_authors(conn)

    conn.close()


def populate_for_paper(paper_id):
    """为单篇论文解析并填充作者信息（供解析 pipeline 调用）。

    新作者的机构名在 parse_author_list 阶段即完成归一化；
    此处不再全局扫描，避免每篇解析都重复归一化全表。
    """
    if not paper_id:
        return
    populate(paper_id=paper_id, normalize_existing=False)


def normalize_existing_authors(conn):
    """对 authors 表中已有机构字段执行归一化更新。"""
    import json as _json
    cur = conn.cursor()
    cur.execute("SELECT id, affiliation, current_affiliation FROM authors")
    updated = 0
    for row in cur.fetchall():
        author_id, aff_json, current = row
        aff_list = []
        if aff_json:
            try:
                parsed = _json.loads(aff_json)
                if isinstance(parsed, list):
                    aff_list = [str(x) for x in parsed if str(x).strip()]
            except _json.JSONDecodeError:
                aff_list = [x.strip() for x in str(aff_json).split(",") if x.strip()]

        normalized_list = normalize_affiliations(aff_list)
        normalized_current = normalize_institution_name(current) if current else None

        new_aff_json = _json.dumps(normalized_list, ensure_ascii=False) if normalized_list else None
        if new_aff_json != aff_json or normalized_current != current:
            cur.execute(
                "UPDATE authors SET affiliation = ?, current_affiliation = ? WHERE id = ?",
                (new_aff_json, normalized_current, author_id),
            )
            updated += 1
    conn.commit()
    print(f"authors 表：归一化更新 {updated} 条机构字段")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="解析并填充 authors / paper_authors 表")
    parser.add_argument("--paper-id", type=int, help="仅处理指定论文 ID")
    args = parser.parse_args()
    populate(paper_id=args.paper_id)
