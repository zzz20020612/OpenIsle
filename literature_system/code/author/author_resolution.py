"""
作者消歧与统一模块

将不同数据源、不同论文中的作者解析为唯一的 author_id，
支持 ORCID / ResearcherID / 姓名+机构 / 合作者网络 / DOI 共现 等多级匹配策略，
并记录匹配方法与置信度。
"""
import json
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from config import SQLITE_PATH


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class AuthorCandidate:
    """从单篇论文解析出的一个作者实例。"""
    given: str = ""
    family: str = ""
    full_name: str = ""
    orcid: Optional[str] = None
    researcher_id: Optional[str] = None
    scopus_author_id: Optional[str] = None
    affiliation: List[str] = field(default_factory=list)
    email: Optional[str] = None
    is_corresponding: bool = False


@dataclass
class AuthorIdentity:
    """数据库中已存在的作者实体。"""
    id: int
    orcid: Optional[str]
    researcher_id: Optional[str]
    scopus_author_id: Optional[str]
    given_name: Optional[str]
    family_name: Optional[str]
    full_name: Optional[str]
    current_affiliation: Optional[str]
    country: Optional[str]
    email: Optional[str]


# ---------------------------------------------------------------------------
# 姓名标准化
# ---------------------------------------------------------------------------

_NAME_CACHE: Dict[str, Tuple[str, str, str]] = {}


def normalize_name(full_name: Optional[str]) -> Tuple[str, str, str]:
    """
    将完整姓名标准化为 (given, family, normalized_full)。
    支持 "Family, Given" / "Given Family" / "G. Family" 等常见写法。
    """
    if not full_name:
        return "", "", ""

    if full_name in _NAME_CACHE:
        return _NAME_CACHE[full_name]

    raw = full_name.strip()
    # 去掉多余空格、点、连字符统一为空格
    raw = re.sub(r"[\.\,\;]", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()

    # "Family, Given" 形式
    if "," in full_name:
        parts = [p.strip() for p in full_name.split(",", 1)]
        family = parts[0]
        given = parts[1]
        norm = f"{given} {family}".strip().lower()
        result = (given.strip(), family.strip(), norm)
        _NAME_CACHE[full_name] = result
        return result

    parts = raw.split()
    if len(parts) == 1:
        result = ("", parts[0], parts[0].lower())
    elif len(parts) == 2:
        result = (parts[0], parts[1], raw.lower())
    else:
        # 取最后一个词为姓氏，前面为名字
        family = parts[-1]
        given = " ".join(parts[:-1])
        result = (given, family, raw.lower())

    _NAME_CACHE[full_name] = result
    return result


def initials(name: str) -> str:
    """提取名字首字母，用于处理 G. / J.-P. 等缩写。"""
    parts = re.sub(r"[^a-zA-Z\-]", " ", name).split()
    initials = []
    for p in parts:
        if "-" in p:
            initials.extend([c[0] for c in p.split("-") if c])
        elif p:
            initials.append(p[0])
    return "".join(initials).upper()


def name_similarity(a: AuthorCandidate, b: AuthorIdentity) -> float:
    """
    计算两个作者姓名的相似度。
    返回 0-1 之间，1 表示完全匹配。
    """
    a_given, a_family, a_full = normalize_name(a.full_name or f"{a.given} {a.family}")
    b_given = b.given_name or ""
    b_family = b.family_name or ""
    b_full = b.full_name or f"{b_given} {b_family}".strip()
    _, _, b_norm = normalize_name(b_full)

    # 姓氏必须相同（忽略大小写）
    if a_family.lower() != b_family.lower():
        return 0.0

    # 全名完全相同
    if a_full.lower() == b_norm:
        return 1.0

    # 名字首字母相同
    a_init = initials(a_given)
    b_init = initials(b_given)
    if a_init and b_init and a_init == b_init:
        return 0.8

    # 名字部分包含
    a_given_lower = a_given.lower()
    b_given_lower = b_given.lower()
    if a_given_lower and b_given_lower and (a_given_lower in b_given_lower or b_given_lower in a_given_lower):
        return 0.7

    return 0.5


# ---------------------------------------------------------------------------
# 机构标准化
# ---------------------------------------------------------------------------

_AFF_STOPWORDS = {
    "university", "college", "institute", "school", "department", "dept",
    "lab", "laboratory", "center", "centre", "academy", "hospital", "faculty",
    "of", "and", "the", "for", "in", "on", "at"
}


def normalize_affiliation(aff: Optional[str]) -> Set[str]:
    """提取机构名中的关键词集合，用于模糊匹配。"""
    if not aff:
        return set()
    tokens = re.findall(r"[a-zA-Z0-9]+", aff.lower())
    return {t for t in tokens if t not in _AFF_STOPWORDS and len(t) > 2}


def affiliation_overlap(a: List[str], b: Optional[str]) -> float:
    """计算两个机构列表的相似度（Jaccard）。"""
    if not a or not b:
        return 0.0
    a_tokens: Set[str] = set()
    for aff in a:
        a_tokens |= normalize_affiliation(aff)
    b_tokens = normalize_affiliation(b)
    if not a_tokens or not b_tokens:
        return 0.0
    intersection = a_tokens & b_tokens
    union = a_tokens | b_tokens
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# 作者解析
# ---------------------------------------------------------------------------


def _clean_orcid(value) -> Optional[str]:
    """清洗 ORCID，支持 URL 前缀与大小写变体。"""
    if not value:
        return None
    value = str(value).strip()
    # 去掉常见 URL 前缀
    value = re.sub(r"^https?://orcid\.org/", "", value, flags=re.IGNORECASE)
    # 基础格式校验
    if re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", value, re.IGNORECASE):
        return value.upper()
    return None


def parse_author_from_source(author_obj: dict) -> AuthorCandidate:
    """将各数据源的作者字典统一转为 AuthorCandidate。"""
    given = author_obj.get("given", "")
    family = author_obj.get("family", "")
    full = author_obj.get("full_name") or f"{given} {family}".strip()
    if not full and family:
        full = family

    aff = author_obj.get("affiliation", [])
    if isinstance(aff, str):
        aff = [aff]
    elif not isinstance(aff, list):
        aff = []

    return AuthorCandidate(
        given=given,
        family=family,
        full_name=full,
        orcid=_clean_orcid(author_obj.get("orcid")),
        researcher_id=_clean_id(author_obj.get("researcher_id")),
        scopus_author_id=_clean_id(author_obj.get("scopus_author_id")),
        affiliation=aff,
        email=author_obj.get("email"),
        is_corresponding=bool(author_obj.get("is_corresponding", False)),
    )


def _clean_id(value) -> Optional[str]:
    if not value:
        return None
    value = str(value).strip()
    if value.lower() in ("none", "null", "nan", ""):
        return None
    return value


def parse_authors_from_paper(author_data) -> List[AuthorCandidate]:
    """解析论文 author 字段（支持 JSON 字符串、列表、字典）。"""
    if isinstance(author_data, str):
        try:
            author_data = json.loads(author_data)
        except json.JSONDecodeError:
            return []
    if isinstance(author_data, dict):
        author_data = [author_data]
    if not isinstance(author_data, list):
        return []
    return [parse_author_from_source(a) for a in author_data if isinstance(a, dict)]


# ---------------------------------------------------------------------------
# 数据库交互
# ---------------------------------------------------------------------------

class AuthorResolver:
    """基于数据库的作者消歧器。"""

    def __init__(self, conn=None):
        self.conn = conn or sqlite3.connect(SQLITE_PATH)
        self.conn.row_factory = sqlite3.Row

    def load_all_identities(self) -> List[AuthorIdentity]:
        cur = self.conn.execute(
            """
            SELECT id, orcid, researcher_id, scopus_author_id,
                   given_name, family_name, full_name,
                   current_affiliation, country, email
            FROM authors
            """
        )
        return [AuthorIdentity(**dict(row)) for row in cur.fetchall()]

    def find_by_orcid(self, orcid: str) -> Optional[AuthorIdentity]:
        normalized = _clean_orcid(orcid)
        if not normalized:
            return None
        cur = self.conn.execute(
            """SELECT id, orcid, researcher_id, scopus_author_id,
                      given_name, family_name, full_name,
                      current_affiliation, country, email
               FROM authors WHERE orcid = ?""",
            (normalized,),
        )
        row = cur.fetchone()
        return AuthorIdentity(**dict(row)) if row else None

    def find_by_researcher_id(self, rid: str) -> Optional[AuthorIdentity]:
        cur = self.conn.execute(
            """SELECT id, orcid, researcher_id, scopus_author_id,
                      given_name, family_name, full_name,
                      current_affiliation, country, email
               FROM authors WHERE researcher_id = ?""",
            (rid,),
        )
        row = cur.fetchone()
        return AuthorIdentity(**dict(row)) if row else None

    def find_by_scopus_id(self, sid: str) -> Optional[AuthorIdentity]:
        cur = self.conn.execute(
            """SELECT id, orcid, researcher_id, scopus_author_id,
                      given_name, family_name, full_name,
                      current_affiliation, country, email
               FROM authors WHERE scopus_author_id = ?""",
            (sid,),
        )
        row = cur.fetchone()
        return AuthorIdentity(**dict(row)) if row else None

    def create_author(self, candidate: AuthorCandidate, match_method: str, match_confidence: str) -> int:
        """在 authors 表新建作者，返回 id。"""
        given, family, full = normalize_name(candidate.full_name or f"{candidate.given} {candidate.family}")
        cur = self.conn.execute(
            """
            INSERT INTO authors (orcid, researcher_id, scopus_author_id,
                                 given_name, family_name, full_name,
                                 current_affiliation, email,
                                 match_method, match_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _clean_orcid(candidate.orcid),
                candidate.researcher_id,
                candidate.scopus_author_id,
                given or None,
                family or None,
                full or None,
                candidate.affiliation[0] if candidate.affiliation else None,
                candidate.email,
                match_method,
                match_confidence,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_author_affiliation(self, author_id: int, new_aff: str):
        """若作者当前机构为空，则用新机构补全。"""
        cur = self.conn.execute(
            "SELECT current_affiliation FROM authors WHERE id = ?", (author_id,)
        )
        row = cur.fetchone()
        if row and not row[0] and new_aff:
            self.conn.execute(
                "UPDATE authors SET current_affiliation = ? WHERE id = ?",
                (new_aff, author_id),
            )
            self.conn.commit()

    def link_paper_author(self, paper_id: int, author_id: int, author_order: int, is_corresponding: bool):
        self.conn.execute(
            """
            INSERT OR REPLACE INTO paper_authors (paper_id, author_id, author_order, is_corresponding)
            VALUES (?, ?, ?, ?)
            """,
            (paper_id, author_id, author_order, int(is_corresponding)),
        )
        self.conn.commit()

    # -----------------------------------------------------------------------
    # 消歧主逻辑
    # -----------------------------------------------------------------------

    def resolve(
        self,
        candidate: AuthorCandidate,
        all_identities: List[AuthorIdentity],
        paper_coauthors: List[str],
    ) -> Tuple[int, str, str]:
        """
        对单个作者候选进行消歧，返回 (author_id, match_method, match_confidence)。
        """
        # 1. ORCID 精确匹配
        if candidate.orcid:
            identity = self.find_by_orcid(candidate.orcid)
            if identity:
                return identity.id, "orcid_exact", "high"

        # 2. Researcher ID 精确匹配
        if candidate.researcher_id:
            identity = self.find_by_researcher_id(candidate.researcher_id)
            if identity:
                return identity.id, "researcher_id_exact", "high"

        # 3. Scopus Author ID 精确匹配
        if candidate.scopus_author_id:
            identity = self.find_by_scopus_id(candidate.scopus_author_id)
            if identity:
                return identity.id, "scopus_id_exact", "high"

        # 4. 姓名 + 机构匹配
        best_match: Optional[AuthorIdentity] = None
        best_score = 0.0
        for identity in all_identities:
            sim = name_similarity(candidate, identity)
            if sim < 0.5:
                continue
            aff_sim = affiliation_overlap(candidate.affiliation, identity.current_affiliation)
            score = sim * 0.6 + aff_sim * 0.4
            if score > best_score:
                best_score = score
                best_match = identity

        if best_match and best_score >= 0.6:
            return best_match.id, "name_affiliation", "medium" if best_score >= 0.75 else "low"

        # 5. 姓名 + 合作者重叠（需要外部传入同篇论文其他作者）
        if paper_coauthors:
            for identity in all_identities:
                sim = name_similarity(candidate, identity)
                if sim < 0.6:
                    continue
                # 简单检查：identity 合作过的论文中是否出现同名合作者
                # 实际实现可扩展为基于 coauthor 表的网络匹配
                coauthor_overlap = self._coauthor_overlap(identity.id, paper_coauthors)
                score = sim * 0.5 + coauthor_overlap * 0.5
                if score >= 0.6:
                    return identity.id, "name_coauthor", "low"

        # 6. 姓名兜底（高相似度）
        if best_match and best_score >= 0.5:
            return best_match.id, "name_only", "low"

        # 7. 新建作者
        author_id = self.create_author(candidate, "new", "none")
        return author_id, "new", "none"

    def _coauthor_overlap(self, author_id: int, coauthor_names: List[str]) -> float:
        """计算作者历史论文合作者与当前候选合作者的重叠度。"""
        if not coauthor_names:
            return 0.0
        cur = self.conn.execute(
            """
            SELECT a.full_name, a.family_name, a.given_name
            FROM paper_authors pa
            JOIN authors a ON pa.author_id = a.id
            WHERE pa.paper_id IN (
                SELECT paper_id FROM paper_authors WHERE author_id = ?
            ) AND pa.author_id != ?
            """,
            (author_id, author_id),
        )
        historical = set()
        for row in cur.fetchall():
            full = row[0] or f"{row[2] or ''} {row[1] or ''}".strip()
            if full:
                historical.add(full.lower())
        if not historical:
            return 0.0
        current = {n.lower() for n in coauthor_names if n}
        overlap = historical & current
        return len(overlap) / max(len(current), 1)

    def resolve_paper_authors(self, paper_id: int, author_data):
        """解析单篇论文的所有作者并建立 paper_authors 关联。"""
        candidates = parse_authors_from_paper(author_data)
        if not candidates:
            return []

        all_identities = self.load_all_identities()
        coauthor_names = [c.full_name for c in candidates]
        results = []

        for order, candidate in enumerate(candidates):
            author_id, method, confidence = self.resolve(
                candidate, all_identities, coauthor_names
            )
            self.link_paper_author(paper_id, author_id, order, candidate.is_corresponding)
            if candidate.affiliation:
                self.update_author_affiliation(author_id, candidate.affiliation[0])

            # 刷新内存中的 identity 列表，避免重复创建
            exists = any(i.id == author_id for i in all_identities)
            if not exists:
                cur = self.conn.execute(
                    """
                    SELECT id, orcid, researcher_id, scopus_author_id,
                           given_name, family_name, full_name,
                           current_affiliation, country, email
                    FROM authors WHERE id = ?
                    """,
                    (author_id,),
                )
                row = cur.fetchone()
                if row:
                    all_identities.append(AuthorIdentity(**dict(row)))

            results.append({
                "author_id": author_id,
                "full_name": candidate.full_name,
                "match_method": method,
                "match_confidence": confidence,
            })

        return results


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def resolve_paper(paper_id: int, author_data, conn=None):
    """对外便捷函数：解析单篇论文作者并写入关联表。"""
    resolver = AuthorResolver(conn)
    return resolver.resolve_paper_authors(paper_id, author_data)


def resolve_all_papers(conn=None):
    """批量处理 papers 表中所有尚未建立 paper_authors 关联的论文。"""
    resolver = AuthorResolver(conn)
    cur = resolver.conn.execute(
        """
        SELECT id, author FROM papers
        WHERE id NOT IN (SELECT DISTINCT paper_id FROM paper_authors)
        AND author IS NOT NULL
        """
    )
    rows = cur.fetchall()
    results = []
    for paper_id, author_data in rows:
        try:
            resolved = resolver.resolve_paper_authors(paper_id, author_data)
            results.append({"paper_id": paper_id, "authors": resolved})
        except Exception as e:
            results.append({"paper_id": paper_id, "error": str(e)})
    return results
