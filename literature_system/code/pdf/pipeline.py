"""
PDF 内容提取 pipeline

解析器优先级链：MinerU API → PyMuPDF → Marker GPU（可配置）

依赖：
    - config.py
    - parse_scheduler.py（状态机）
    - 数据库表 paper_fulltext / paper_sections / paper_figures
    - pdfs/ 目录下的 PDF 文件
"""
import os
import re
import json
import time
import shutil
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import config
from logger import get_logger
from pdf.scheduler import (
    get_conn, get_job, update_job, classify_error,
    get_parser_chain, mineru_quota_exceeded, get_mineru_usage_today,
)

log = get_logger("pdf_pipeline")


# ============================================================
# 工具函数
# ============================================================
def safe_doi(doi: str) -> str:
    """把 DOI 转为文件名安全的字符串（与 downloader.py 保持一致）。"""
    if not doi:
        return "unknown"
    return doi.replace('/', '_').replace(':', '_').replace('\\', '_').replace('?', '_').replace('*', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')[:120]


def get_pdf_path(paper_id: int, doi: Optional[str] = None) -> Optional[Path]:
    """根据 paper_id/DOI 找到本地 PDF 文件。"""
    pdf_dir = Path(config.PDF_DOWNLOAD_DIR)
    if doi:
        candidate = pdf_dir / f"{safe_doi(doi)}.pdf"
        if candidate.exists():
            return candidate
    # 兜底：扫描 pdfs/ 下任意以 paper_id 命名的文件
    for f in pdf_dir.glob(f"*{paper_id}*.pdf"):
        return f
    return None


# ============================================================
# 章节类型分类器
# ============================================================
SECTION_RULES = [
    ("abstract",       re.compile(r"^\s*abstract\b", re.I)),
    ("intro",          re.compile(r"^\s*(introduction|background)\b", re.I)),
    ("methods",        re.compile(r"^\s*(methods?|materials?\s+and\s+methods?|study\s+area|data\s+collection)\b", re.I)),
    ("results",        re.compile(r"^\s*(results?|findings?|results?\s+and\s+discussion)\b", re.I)),
    ("discussion",     re.compile(r"^\s*discussion\b", re.I)),
    ("conclusion",     re.compile(r"^\s*conclusions?\b", re.I)),
    ("references",     re.compile(r"^\s*(references?|bibliography|works?\s+cited)\b", re.I)),
    ("acknowledgments", re.compile(r"^\s*acknowledg", re.I)),
    ("appendix",       re.compile(r"^\s*(appendix|supplementary)\b", re.I)),
    ("data_availability", re.compile(r"^\s*data\s+availability\b", re.I)),
]


def classify_section(heading: str) -> str:
    """根据标题关键词判断章节类型。"""
    if not heading:
        return "other"
    for sec_type, pattern in SECTION_RULES:
        if pattern.match(heading.strip()):
            return sec_type
    return "other"


def markdown_to_plain(md: str) -> str:
    """把 Markdown 粗略转为纯文本。"""
    # 去掉图片引用
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    # 去掉链接，保留文本
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    # 去掉标题井号
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 去掉强调
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text.strip()


# ============================================================
# 统一中间格式
# ============================================================
class UnifiedResult:
    """统一解析结果，下游入库均基于此。"""

    def __init__(self):
        self.parser_used: str = ""
        self.parse_quality: str = "medium"  # high/medium/low
        self.full_text: str = ""
        self.full_markdown: Optional[str] = None
        self.sections: List[Dict[str, Any]] = []
        self.figures: List[Dict[str, Any]] = []
        self.tables: List[Dict[str, Any]] = []
        self.references: List[Dict[str, Any]] = []
        self.page_count: int = 0
        self.char_count: int = 0
        self.mineru_task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parser_used": self.parser_used,
            "parse_quality": self.parse_quality,
            "full_text": self.full_text,
            "full_markdown": self.full_markdown,
            "sections": self.sections,
            "figures": self.figures,
            "tables": self.tables,
            "references": self.references,
            "page_count": self.page_count,
            "char_count": self.char_count,
            "mineru_task_id": self.mineru_task_id,
        }

    def validate(self) -> bool:
        """基本校验：至少要有 full_text。"""
        return bool(self.full_text) and len(self.full_text) > 100


# ============================================================
# PyMuPDF 解析器（兜底）
# ============================================================
class PyMuPDFParser:
    """快速纯文本解析器，无结构信息，质量 low。"""

    name = "pymupdf"

    def parse(self, pdf_path: Path) -> UnifiedResult:
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise RuntimeError("PyMuPDF(fitz) 未安装，请 pip install pymupdf")

        result = UnifiedResult()
        result.parser_used = self.name
        result.parse_quality = "low"

        doc = fitz.open(str(pdf_path))
        result.page_count = len(doc)
        text_parts = []
        current_heading = None
        current_section_text = []
        sections_raw: List[Tuple[str, str]] = []

        for page_idx, page in enumerate(doc):
            page_text = page.get_text()
            text_parts.append(page_text)
            # 简单的章节识别：行很短且首字母大写、且匹配关键词
            for line in page_text.splitlines():
                stripped = line.strip()
                if not stripped or len(stripped) > 80:
                    if current_heading is not None:
                        current_section_text.append(stripped)
                    continue
                # 章节标题判定
                if classify_section(stripped) != "other":
                    if current_heading is not None:
                        sections_raw.append((current_heading, "\n".join(current_section_text)))
                    current_heading = stripped
                    current_section_text = []
        if current_heading is not None:
            sections_raw.append((current_heading, "\n".join(current_section_text)))

        doc.close()

        result.full_text = "\n".join(text_parts)
        result.full_markdown = None  # PyMuPDF 不输出 Markdown
        result.char_count = len(result.full_text)

        # 构建章节
        for idx, (heading, content) in enumerate(sections_raw):
            result.sections.append({
                "section_type": classify_section(heading),
                "heading": heading,
                "content": content,
                "page_start": None,
                "page_end": None,
                "order_idx": idx,
            })

        log.info(f"[pymupdf] {pdf_path.name}: {result.char_count} chars, "
                 f"{result.page_count} pages, {len(result.sections)} sections")
        return result


# ============================================================
# MinerU API 客户端
# ============================================================
class MineruAPIError(Exception):
    """MinerU API 异常基类，附带 error_class。"""
    def __init__(self, msg: str, error_class: str = "mineru_upload_failed", parser: str = "mineru_api"):
        super().__init__(msg)
        self.error_class = error_class
        self.parser = parser
        self.context = "mineru"


class MineruAPIClient:
    """MinerU 云端解析客户端（v4 batch API）。

    正确流程：
      1. POST /file-urls/batch → 返回 batch_id + 每个文件的 PUT 上传 URL
      2. PUT 文件到上传 URL
      3. GET /extract-results/batch/{batch_id} 轮询，state=done 时取 full_zip_url
      4. 下载 zip，解压到本地
      5. 转换为 UnifiedResult
    """

    name = "mineru_api"
    BASE_URL = "https://mineru.net/api/v4"

    def __init__(self):
        if not config.MINERU_API_KEY:
            raise MineruAPIError("MINERU_API_KEY 未配置", error_class="mineru_upload_failed")
        self.api_key = config.MINERU_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def parse(self, pdf_path: Path) -> UnifiedResult:
        """完整流程：申请上传 URL → PUT 文件 → 轮询结果 → 下载 → 转换。"""
        # 配额检查
        if mineru_quota_exceeded():
            raise MineruAPIError(
                f"今日 MinerU 已用 {get_mineru_usage_today()} 次，超出配额 {config.MINERU_DAILY_QUOTA}",
                error_class="mineru_quota_exceeded",
            )

        # 1. 申请上传 URL（创建批次）
        batch_id, put_url = self._create_batch(pdf_path)

        # 2. PUT 上传文件
        self._upload_file(pdf_path, put_url)

        # 3. 轮询批次结果
        result_url = self._poll_batch(batch_id, pdf_path)

        # 4. 下载结果包
        result_dir = self._download_result(batch_id, result_url, pdf_path)

        # 5. 转换为统一格式
        result = self._convert_result(result_dir, pdf_path)
        result.parser_used = self.name
        result.parse_quality = "high"
        result.mineru_task_id = batch_id
        return result

    # ------ 申请上传 URL（创建批次）------
    def _create_batch(self, pdf_path: Path) -> Tuple[str, str]:
        """POST /file-urls/batch 申请上传 URL，返回 (batch_id, put_url)。"""
        url = f"{self.BASE_URL}/file-urls/batch"
        payload = {
            "enable_formula": True,
            "enable_table": True,
            "language": "en",
            "files": [
                {
                    "name": pdf_path.name,
                    "is_ocr": False,
                }
            ],
        }
        try:
            r = requests.post(url, headers=self.headers, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            if data.get("code") != 0:
                raise MineruAPIError(
                    f"批次创建失败: {data.get('msg', '未知错误')}",
                    error_class="mineru_upload_failed",
                )
            batch_id = data["data"]["batch_id"]
            file_urls = data["data"]["file_urls"]
            if not file_urls:
                raise MineruAPIError("批次创建返回空 file_urls",
                                     error_class="mineru_upload_failed")
            log.info(f"[mineru] 批次创建成功: batch_id={batch_id}")
            return batch_id, file_urls[0]
        except (requests.RequestException, KeyError, IndexError) as e:
            raise MineruAPIError(f"批次创建异常: {e}", error_class="mineru_upload_failed")

    # ------ 上传 ------
    def _upload_file(self, pdf_path: Path, put_url: str):
        """PUT 文件到上传 URL。"""
        try:
            with open(pdf_path, "rb") as f:
                put_r = requests.put(put_url, data=f, timeout=config.MINERU_UPLOAD_TIMEOUT)
                put_r.raise_for_status()
            log.info(f"[mineru] 文件上传成功: {pdf_path.name}")
        except requests.RequestException as e:
            raise MineruAPIError(f"文件上传失败: {e}", error_class="mineru_upload_failed")

    # ------ 轮询批次结果 ------
    def _poll_batch(self, batch_id: str, pdf_path: Path) -> str:
        """GET /extract-results/batch/{batch_id} 轮询，返回 full_zip_url。"""
        poll_url = f"{self.BASE_URL}/extract-results/batch/{batch_id}"
        wait_interval = config.MINERU_TASK_POLL_INTERVAL
        max_wait = config.MINERU_TASK_MAX_WAIT
        elapsed = 0
        target_name = pdf_path.name.lower()

        while elapsed < max_wait:
            try:
                r = requests.get(poll_url, headers=self.headers, timeout=30)
                r.raise_for_status()
                data = r.json().get("data", {})
                extract_result = data.get("extract_result", [])
                # 找到对应文件的解析结果（按 file_name 匹配）
                for item in extract_result:
                    fname = (item.get("file_name") or "").lower()
                    if fname and fname != target_name:
                        continue
                    state = item.get("state")
                    if state == "done":
                        zip_url = item.get("full_zip_url")
                        if not zip_url:
                            raise MineruAPIError(
                                f"任务完成但无 full_zip_url: {item}",
                                error_class="mineru_task_timeout",
                            )
                        log.info(f"[mineru] 任务完成 batch_id={batch_id}, 耗时 {elapsed}s")
                        return zip_url
                    elif state == "failed":
                        err = item.get("err_msg") or "未知错误"
                        raise MineruAPIError(f"任务失败: {err}",
                                             error_class="mineru_task_timeout")
                    # 仍在处理中，继续轮询
                # 当前文件未完成
                time.sleep(wait_interval)
                elapsed += wait_interval
                if elapsed % 60 == 0:
                    log.info(f"[mineru] 等待 batch_id={batch_id}，已 {elapsed}s")
            except requests.RequestException as e:
                log.warning(f"[mineru] 轮询异常，将重试: {e}")
                time.sleep(wait_interval)
                elapsed += wait_interval

        raise MineruAPIError(f"任务超时未完成 batch_id={batch_id}，等待 {max_wait}s",
                             error_class="mineru_task_timeout")

    # ------ 下载结果 ------
    def _download_result(self, batch_id: str, result_url: str, pdf_path: Path) -> Path:
        """下载结果 zip，解压到本地目录。"""
        import zipfile
        import io

        result_dir = Path(config.PDF_DOWNLOAD_DIR) / "mineru_results" / safe_doi(pdf_path.stem)
        result_dir.mkdir(parents=True, exist_ok=True)

        try:
            r = requests.get(result_url, timeout=120, stream=True)
            r.raise_for_status()
            zip_bytes = r.content
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                zf.extractall(result_dir)
            log.info(f"[mineru] 结果下载完成: {result_dir}")
            return result_dir
        except (requests.RequestException, zipfile.BadZipFile) as e:
            raise MineruAPIError(f"结果下载失败: {e}", error_class="mineru_task_timeout")

    # ------ 转换为统一格式 ------
    def _convert_result(self, result_dir: Path, pdf_path: Path) -> UnifiedResult:
        """读取 MinerU 输出目录，转为 UnifiedResult。"""
        result = UnifiedResult()

        # 找 full.md
        full_md_path = result_dir / "full.md"
        if full_md_path.exists():
            result.full_markdown = full_md_path.read_text(encoding="utf-8")
            result.full_text = markdown_to_plain(result.full_markdown)
        else:
            # 兜底：扫描子目录
            for sub in result_dir.iterdir():
                if sub.is_dir():
                    md_file = sub / "full.md"
                    if md_file.exists():
                        result_dir = sub
                        result.full_markdown = md_file.read_text(encoding="utf-8")
                        result.full_text = markdown_to_plain(result.full_markdown)
                        break

        if not result.full_text:
            raise MineruAPIError(f"未找到 full.md: {result_dir}", error_class="mineru_task_timeout")

        result.char_count = len(result.full_text)

        # 找 content_list.json
        content_list_path = None
        for p in result_dir.rglob("*content_list*.json"):
            content_list_path = p
            break

        if content_list_path:
            self._parse_content_list(content_list_path, result_dir, result, pdf_path)

        log.info(f"[mineru] {pdf_path.name}: {result.char_count} chars, "
                 f"{result.page_count} pages, {len(result.sections)} sections, "
                 f"{len(result.figures)} figures, {len(result.tables)} tables")
        return result

    def _parse_content_list(self, content_list_path: Path, result_dir: Path,
                             result: UnifiedResult, pdf_path: Path):
        """解析 MinerU 的 content_list.json。"""
        try:
            blocks = json.loads(content_list_path.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"[mineru] content_list 解析失败: {e}")
            return

        # 把图片复制到统一的 figures 目录
        figures_dir = Path(config.PDF_DOWNLOAD_DIR) / "figures" / safe_doi(pdf_path.stem)
        figures_dir.mkdir(parents=True, exist_ok=True)

        # 章节切分：根据 text_level==1 或 2 的 text 块作为分隔
        current_section = {"heading": None, "content": [], "page_start": None, "page_end": None}
        sections_raw: List[Dict[str, Any]] = []
        max_page = 0
        fig_idx = 0
        tbl_idx = 0

        for block in blocks:
            btype = block.get("type")
            page_idx = block.get("page_idx", 0)
            max_page = max(max_page, page_idx)

            if btype == "text" and block.get("text_level") in (1, 2):
                # 新章节标题
                if current_section["heading"] is not None:
                    sections_raw.append({
                        "heading": current_section["heading"],
                        "content": "\n".join(current_section["content"]),
                        "page_start": current_section["page_start"],
                        "page_end": current_section["page_end"],
                    })
                current_section = {
                    "heading": block.get("text", "").strip(),
                    "content": [],
                    "page_start": page_idx,
                    "page_end": page_idx,
                }
            elif btype == "text":
                text = block.get("text", "").strip()
                if text:
                    current_section["content"].append(text)
                    current_section["page_end"] = page_idx
            elif btype == "list":
                # list 块（MinerU 把参考文献、列表项放这里），list_items 是数组
                list_items = block.get("list_items", [])
                if list_items:
                    # 每条 list item 作为一行
                    list_text = "\n".join(item.strip() for item in list_items if item)
                    if list_text:
                        current_section["content"].append(list_text)
                        current_section["page_end"] = page_idx
            elif btype == "image":
                img_path = block.get("img_path", "")
                caption_list = block.get("image_caption", [])
                caption = caption_list[0] if caption_list else ""
                if img_path:
                    src = result_dir / img_path
                    if src.exists():
                        dst = figures_dir / Path(img_path).name
                        shutil.copy(src, dst)
                        rel_path = str(dst.relative_to(Path(config.PDF_DOWNLOAD_DIR).parent))
                    else:
                        rel_path = img_path
                else:
                    rel_path = ""
                fig_idx += 1
                result.figures.append({
                    "fig_label": f"Fig {fig_idx}",
                    "fig_type": "figure",
                    "caption": caption,
                    "file_path": rel_path,
                    "page": page_idx,
                })
            elif btype == "table":
                caption_list = block.get("table_caption", [])
                caption = caption_list[0] if caption_list else ""
                table_body = block.get("table_body", "")
                tbl_idx += 1
                result.tables.append({
                    "fig_label": f"Table {tbl_idx}",
                    "fig_type": "table",
                    "caption": caption,
                    "markdown_content": table_body,
                    "page": page_idx,
                })

        # 末尾章节
        if current_section["heading"] is not None:
            sections_raw.append({
                "heading": current_section["heading"],
                "content": "\n".join(current_section["content"]),
                "page_start": current_section["page_start"],
                "page_end": current_section["page_end"],
            })

        result.page_count = max_page + 1

        for idx, sec in enumerate(sections_raw):
            result.sections.append({
                "section_type": classify_section(sec["heading"]),
                "heading": sec["heading"],
                "content": sec["content"],
                "page_start": sec["page_start"],
                "page_end": sec["page_end"],
                "order_idx": idx,
            })


# ============================================================
# 章节后处理：噪声过滤 + other 归并 + PyMuPDF 补充
# ============================================================

# 论文头部噪声关键词（出现在标题中即视为噪声块）
NOISE_KEYWORDS = [
    "title:", "authors", "affiliations", "keywords",
    "corresponding author", "email", "orcid",
]

# 内容关键词（用于 other 章节归属判定）
METHOD_KEYWORDS = ["method", "protocol", "software", "qgis", "gimp", "vectorized",
                   "calculated", "we used", "we selected", "we combined",
                   "cadastral", "shapefile", "plugin", "wms", "web map service",
                   "data collection", "mapping", "geospatial", "formula", "equation"]
RESULT_KEYWORDS = ["result", "finding", "we obtained", "we found", "we observed",
                   "figure shows", "table shows", "significant", "correlation"]
SUPPLEMENT_KEYWORDS = ["supplementary", "supporting information", "table s1",
                      "figure s1", "appendix s"]


def _is_noise_section(heading: str, content: str, page_start: Optional[int] = None) -> bool:
    """判断是否为论文头部噪声块。"""
    if not heading:
        return True
    h = heading.strip().lower()
    if not content and len(heading) < 80:
        return True
    for kw in NOISE_KEYWORDS:
        if kw in h:
            return True
    if h.startswith("title:"):
        return True
    # 第 0 页且内容很短（标题页）
    if page_start == 0 and len(content) < 200:
        return True
    return False


def _classify_other_section(heading: str, content: str,
                              prev_type: Optional[str], next_type: Optional[str]) -> str:
    """智能判定 other 章节应归并到哪种类型。"""
    h = heading.lower()
    c = (content or "").lower()

    # 1. 特殊关键词优先
    for kw in SUPPLEMENT_KEYWORDS:
        if kw in h or kw in c[:200]:
            return "supplementary_material"

    # 2. 前后类型相同 → 归并
    if prev_type and next_type and prev_type == next_type and prev_type != "other":
        return prev_type

    # 3. 用内容关键词判定
    method_score = sum(1 for kw in METHOD_KEYWORDS if kw in c[:500])
    result_score = sum(1 for kw in RESULT_KEYWORDS if kw in c[:500])

    if method_score > result_score and method_score > 0:
        return "methods"
    if result_score > method_score and result_score > 0:
        return "results"

    # 4. 前一章节类型决定
    if prev_type == "methods":
        return "methods"
    if prev_type == "results":
        return "results"

    return "other"


def _post_process_sections(sections: List[Dict[str, Any]],
                            pdf_path: Optional[Path] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """章节后处理：噪声过滤 + other 归并 + PyMuPDF 空内容补充。

    Returns: (processed_sections, removed_noise_sections)
    """
    if not sections:
        return sections, []

    # 1. 噪声过滤
    filtered = []
    removed = []
    for sec in sections:
        if _is_noise_section(sec.get("heading", ""), sec.get("content", ""),
                              sec.get("page_start")):
            removed.append(sec)
        else:
            filtered.append(sec)

    # 2. other 章节智能归并
    for i, sec in enumerate(filtered):
        if sec.get("section_type") == "other":
            prev_type = filtered[i - 1].get("section_type") if i > 0 else None
            next_type = (filtered[i + 1].get("section_type")
                         if i + 1 < len(filtered) else None)
            new_type = _classify_other_section(
                sec.get("heading", ""), sec.get("content", ""), prev_type, next_type
            )
            if new_type != "other":
                sec["section_type"] = new_type
                sec["reclassified_from"] = "other"

    # 3. PyMuPDF 空内容章节补充（仅当 pdf_path 可用时）
    if pdf_path:
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            pages_text = [page.get_text() for page in doc]
            doc.close()

            for sec in filtered:
                content_len = len(sec.get("content", "") or "")
                if content_len < 50:
                    page_start = sec.get("page_start")
                    page_end = sec.get("page_end")
                    if page_start is not None and page_end is not None:
                        start = max(0, page_start)
                        end = min(len(pages_text) - 1, page_end)
                        pymupdf_content = "\n".join(pages_text[start:end + 1])
                        if pymupdf_content and len(pymupdf_content) > content_len:
                            sec["content"] = pymupdf_content
                            sec["supplemented_by"] = "pymupdf"
        except ImportError:
            pass  # PyMuPDF 未安装，跳过

    # 4. 重新排序 order_idx
    for idx, sec in enumerate(filtered):
        sec["order_idx"] = idx

    return filtered, removed


# ============================================================
# Pipeline 主类（被 parse_scheduler 调用）
# ============================================================
class PdfPipeline:
    """PDF 解析 pipeline 入口，按优先级链调用解析器。"""

    def __init__(self):
        self.chain = get_parser_chain()
        log.info(f"解析器优先级链: {self.chain}")

    def run(self, paper_id: int, job_id: int) -> Dict[str, Any]:
        """运行完整 pipeline，返回解析器与统计信息。"""
        # 1. 查找论文与 PDF 路径
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, doi, title FROM papers WHERE id = ?", (paper_id,))
        paper = cur.fetchone()
        conn.close()
        if not paper:
            raise RuntimeError(f"paper_id={paper_id} 不存在")

        pdf_path = get_pdf_path(paper_id, paper["doi"])
        if not pdf_path or not pdf_path.exists():
            err = RuntimeError(f"未找到 PDF 文件 (paper_id={paper_id}, doi={paper['doi']})")
            err.error_class = "http_404"
            err.parser = "pipeline"
            raise err

        log.info(f"开始解析 paper_id={paper_id} doi={paper['doi']} file={pdf_path.name}")

        # 2. 按优先级链尝试解析器
        last_error = None
        for parser_name in self.chain:
            try:
                if parser_name == "mineru_api":
                    if not config.MINERU_API_KEY:
                        log.info("[chain] 跳过 mineru_api：未配置 API_KEY")
                        continue
                    parser = MineruAPIClient()
                elif parser_name == "pymupdf":
                    parser = PyMuPDFParser()
                elif parser_name in ("marker_gpu", "marker_cpu"):
                    # Marker 暂不集成，留作扩展点
                    log.info(f"[chain] 暂未集成 {parser_name}，跳过")
                    continue
                else:
                    continue

                update_job(job_id, parser_used=parser_name)
                log.info(f"[chain] 尝试 {parser_name}")
                result = parser.parse(pdf_path)

                if not result.validate():
                    raise RuntimeError(f"{parser_name} 输出无效（full_text 过短）")

                # 3. 章节后处理：噪声过滤 + other 归并 + PyMuPDF 补充
                processed_sections, removed_noise = _post_process_sections(
                    result.sections, pdf_path
                )
                result.sections = processed_sections
                log.info(f"[post] 章节后处理: {len(removed_noise)} 噪声块过滤, "
                         f"{len(processed_sections)} 章节保留")

                # 4. 入库
                self._save_to_db(paper_id, result)
                log.info(f"✓ paper_id={paper_id} 解析成功，使用 {parser_name}")
                return {"parser_used": parser_name, "result": result.to_dict()}

            except MineruAPIError as e:
                log.warning(f"[chain] {parser_name} 失败: {e.error_class} - {e}")
                last_error = e
                # 配额超限不再重试 MinerU
                if e.error_class == "mineru_quota_exceeded":
                    log.warning("[chain] MinerU 配额超限，剩余 PDF 跳过 mineru_api")
                continue
            except Exception as e:
                log.warning(f"[chain] {parser_name} 异常: {e}")
                last_error = e
                continue

        # 所有解析器都失败
        if last_error:
            raise last_error
        raise RuntimeError("无可用解析器")

    def _save_to_db(self, paper_id: int, result: UnifiedResult):
        """把统一结果写入数据库。"""
        conn = get_conn()
        cur = conn.cursor()
        try:
            # paper_fulltext（UPSERT）
            cur.execute(
                """INSERT INTO paper_fulltext
                   (paper_id, parser_used, parse_quality, full_text, full_markdown,
                    char_count, page_count, parsed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(paper_id) DO UPDATE SET
                     parser_used=excluded.parser_used,
                     parse_quality=excluded.parse_quality,
                     full_text=excluded.full_text,
                     full_markdown=excluded.full_markdown,
                     char_count=excluded.char_count,
                     page_count=excluded.page_count,
                     parsed_at=excluded.parsed_at""",
                (paper_id, result.parser_used, result.parse_quality,
                 result.full_text, result.full_markdown, result.char_count,
                 result.page_count, datetime.now().isoformat()),
            )

            # paper_sections（先删后插）
            cur.execute("DELETE FROM paper_sections WHERE paper_id = ?", (paper_id,))
            for sec in result.sections:
                cur.execute(
                    """INSERT INTO paper_sections
                       (paper_id, section_type, heading, content, page_start, page_end, order_idx)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (paper_id, sec["section_type"], sec["heading"], sec["content"],
                     sec.get("page_start"), sec.get("page_end"), sec["order_idx"]),
                )

            # paper_figures（先删后插，覆盖 figures 与 tables）
            cur.execute("DELETE FROM paper_figures WHERE paper_id = ?", (paper_id,))
            for fig in result.figures:
                cur.execute(
                    """INSERT INTO paper_figures
                       (paper_id, fig_label, fig_type, caption, file_path, page)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (paper_id, fig["fig_label"], fig["fig_type"],
                     fig.get("caption", ""), fig.get("file_path", ""), fig.get("page")),
                )
            for tbl in result.tables:
                cur.execute(
                    """INSERT INTO paper_figures
                       (paper_id, fig_label, fig_type, caption, file_path, page)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (paper_id, tbl["fig_label"], "table",
                     tbl.get("caption", ""), tbl.get("markdown_content", ""), tbl.get("page")),
                )

            conn.commit()
            log.info(f"[db] 已写入 paper_id={paper_id}: "
                     f"fulltext({result.char_count} chars) + "
                     f"{len(result.sections)} sections + "
                     f"{len(result.figures) + len(result.tables)} figures/tables")
        finally:
            conn.close()

        # 触发参考文献解析（异步、不影响主流程）
        self._extract_references_async(paper_id, result)

    def _extract_references_async(self, paper_id: int, result: UnifiedResult):
        """从解析结果中提取 References 章节文本，调用 ref_parser 入库 citations_v2。"""
        try:
            from pdf.ref_parser import extract_and_save_references
            # 查找 DOI
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT doi FROM papers WHERE id = ?", (paper_id,))
            row = cur.fetchone()
            conn.close()
            doi = row["doi"] if row else None

            # 找 References 章节
            ref_text = ""
            for sec in result.sections:
                if sec.get("section_type") == "references":
                    ref_text = sec.get("content", "")
                    break
            if not ref_text:
                log.info(f"[ref] paper_id={paper_id} 无 References 章节，跳过")
                return

            stats = extract_and_save_references(
                paper_id=paper_id,
                doi=doi,
                references_section_text=ref_text,
                doi_lookup_limit=10,  # 反查前 10 个 DOI 的元数据
            )
            log.info(f"[ref] paper_id={paper_id} 参考文献入库: {stats}")
        except Exception as e:
            log.warning(f"[ref] paper_id={paper_id} 参考文献解析失败（不影响主流程）: {e}")


if __name__ == "__main__":
    # 简单自测入口
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", help="直接解析本地 PDF 文件（不入库）")
    ap.add_argument("--parser", default="pymupdf", choices=["pymupdf", "mineru_api"])
    args = ap.parse_args()

    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            print(f"文件不存在: {pdf_path}")
            raise SystemExit(1)
        if args.parser == "pymupdf":
            r = PyMuPDFParser().parse(pdf_path)
        else:
            r = MineruAPIClient().parse(pdf_path)
        print(json.dumps({
            "parser_used": r.parser_used,
            "parse_quality": r.parse_quality,
            "char_count": r.char_count,
            "page_count": r.page_count,
            "sections": len(r.sections),
            "figures": len(r.figures),
            "tables": len(r.tables),
        }, ensure_ascii=False, indent=2))
