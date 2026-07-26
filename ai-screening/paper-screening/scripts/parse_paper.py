"""Paper parsing module for extracting text, metadata, and structure from academic papers.

Supports PDF, DOCX, TXT, and TEX formats. Outputs a unified JSON structure with
metadata, segments, images, tables, and declarations.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def parse_paper(file_path: str) -> dict[str, Any]:
    """Parse a paper file and return a unified structured JSON.

    Args:
        file_path: Path to the paper file (PDF, DOCX, TXT, or TEX).

    Returns:
        Dict with keys: metadata, segments, images, tables, declarations.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file format is unsupported.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()
    dispatch = {
        ".txt": _parse_txt,
        ".pdf": _parse_pdf,
        ".docx": _parse_docx,
        ".tex": _parse_tex,
    }
    parser = dispatch.get(suffix)
    if parser is None:
        raise ValueError(f"Unsupported format: {suffix}")
    return parser(path)


# ---------------------------------------------------------------------------
# Section pattern matching (shared by TXT and DOCX)
# ---------------------------------------------------------------------------

_SECTION_PATTERNS: dict[str, re.Pattern] = {
    "abstract": re.compile(r"(?i)^#{0,3}\s*abstract"),
    "introduction": re.compile(r"(?i)^#{0,3}\s*introduction"),
    "methods": re.compile(r"(?i)^#{0,3}\s*(?:methods?|methodology)"),
    "results": re.compile(r"(?i)^#{0,3}\s*results?"),
    "discussion": re.compile(r"(?i)^#{0,3}\s*discussion"),
    "conclusion": re.compile(r"(?i)^#{0,3}\s*conclusions?"),
    "references": re.compile(r"(?i)^#{0,3}\s*references?"),
}


def _detect_section(text: str) -> str | None:
    """Return section type if *text* matches a known section heading, else None."""
    for stype, pat in _SECTION_PATTERNS.items():
        if pat.match(text):
            return stype
    return None


def _extract_title_from_text(text: str) -> str:
    """Extract title as the first non-empty line (max 200 chars)."""
    for line in text.strip().split("\n"):
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return "Untitled"


def _segment_paragraphs(text: str, confidence: float = 0.7) -> list[dict[str, Any]]:
    """Split *text* on blank lines and classify each paragraph into sections."""
    sections: list[dict[str, Any]] = []
    current_type = "body"

    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue

        detected = _detect_section(para)
        if detected is not None:
            current_type = detected

        sections.append({
            "type": current_type,
            "text": para[:5000],
            "page_start": 1,
            "page_end": 1,
            "confidence": confidence,
        })

    return sections


# ---------------------------------------------------------------------------
# TXT
# ---------------------------------------------------------------------------

def _parse_txt(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")

    metadata = {
        "format": "txt",
        "title": _extract_title_from_text(text),
        "authors": [],
        "has_abstract": bool(re.search(r"(?i)abstract", text)),
        "page_count": 1,
        "file_size_bytes": path.stat().st_size,
    }

    return {
        "metadata": metadata,
        "segments": _segment_paragraphs(text),
        "images": [],
        "tables": [],
        "declarations": {},
    }


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _parse_pdf(path: Path) -> dict[str, Any]:
    try:
        import pdfplumber  # type: ignore[import-untyped]
        return _parse_pdf_pdfplumber(path)
    except ImportError:
        pass

    try:
        from pypdf import PdfReader  # type: ignore[import-untyped]
        return _parse_pdf_pypdf(path)
    except ImportError:
        pass

    raise ImportError("Install pdfplumber or pypdf: pip install pdfplumber pypdf")


def _parse_pdf_pdfplumber(path: Path) -> dict[str, Any]:
    import pdfplumber  # noqa: F811 – repeated import is intentional for lazy load

    with pdfplumber.open(path) as pdf:
        full_text_parts: list[str] = []
        segments: list[dict[str, Any]] = []
        current_type = "body"

        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            full_text_parts.append(text)

            for para in re.split(r"\n\s*\n", text):
                para = para.strip()
                if not para:
                    continue
                detected = _detect_section(para)
                if detected is not None:
                    current_type = detected
                segments.append({
                    "type": current_type,
                    "text": para[:5000],
                    "page_start": page_num,
                    "page_end": page_num,
                    "confidence": 0.7,
                })

        full_text = "\n".join(full_text_parts)
        title = pdf.metadata.get("Title", "") if pdf.metadata else ""
        if not title:
            title = _extract_title_from_text(full_text)

        metadata = {
            "format": "pdf",
            "title": title,
            "authors": [],
            "has_abstract": bool(re.search(r"(?i)abstract", full_text)),
            "page_count": len(pdf.pages),
            "file_size_bytes": path.stat().st_size,
        }

    return {
        "metadata": metadata,
        "segments": segments,
        "images": [],
        "tables": [],
        "declarations": {},
    }


def _parse_pdf_pypdf(path: Path) -> dict[str, Any]:
    from pypdf import PdfReader  # noqa: F811

    reader = PdfReader(path)
    full_text_parts: list[str] = []
    segments: list[dict[str, Any]] = []
    current_type = "body"

    for page_num, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        full_text_parts.append(text)

        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if not para:
                continue
            detected = _detect_section(para)
            if detected is not None:
                current_type = detected
            segments.append({
                "type": current_type,
                "text": para[:5000],
                "page_start": page_num,
                "page_end": page_num,
                "confidence": 0.7,
            })

    full_text = "\n".join(full_text_parts)
    title = ""
    if reader.metadata:
        title = reader.metadata.get("/Title", "") or ""
    if not title:
        title = _extract_title_from_text(full_text)

    metadata = {
        "format": "pdf",
        "title": title,
        "authors": [],
        "has_abstract": bool(re.search(r"(?i)abstract", full_text)),
        "page_count": len(reader.pages),
        "file_size_bytes": path.stat().st_size,
    }

    return {
        "metadata": metadata,
        "segments": segments,
        "images": [],
        "tables": [],
        "declarations": {},
    }



# ---------------------------------------------------------------------------
# PDF page image extraction (for multimodal analysis)
# ---------------------------------------------------------------------------

def _extract_pdf_page_images(
    path: Path,
    max_pages: int = 10,
    max_width: int = 1200,
) -> list[dict[str, Any]]:
    """将 PDF 前 N 页渲染为 base64 PNG，用于多模态 LLM 分析。

    Args:
        path: PDF 文件路径。
        max_pages: 最多提取页数，默认 10。
        max_width: 最大像素宽度，超过时等比缩放，默认 1200。

    Returns:
        [{page, base64, width, height}]，失败时返回空列表。
    """
    try:
        import pdfplumber  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("pdfplumber 未安装，无法提取 PDF 页面图像")
        return []

    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("Pillow 未安装，无法进行图像缩放，跳过图像提取")
        return []

    images: list[dict[str, Any]] = []

    try:
        with pdfplumber.open(path) as pdf:
            pages_to_render = pdf.pages[:max_pages]

            for page_num, page in enumerate(pages_to_render, 1):
                try:
                    page_image = page.to_image(resolution=150)
                    pil_img = page_image.original  # type: ignore[attr-defined]

                    w, h = pil_img.size
                    if w > max_width:
                        ratio = max_width / w
                        new_h = int(h * ratio)
                        pil_img = pil_img.resize(
                            (max_width, new_h), Image.LANCZOS
                        )
                        w, h = max_width, new_h

                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    b64_str = base64.b64encode(buf.getvalue()).decode("ascii")

                    images.append({
                        "page": page_num,
                        "base64": b64_str,
                        "width": w,
                        "height": h,
                    })
                except Exception as exc:
                    logger.warning("第 %d 页图像渲染失败: %s", page_num, exc)
                    continue

    except Exception as exc:
        logger.warning("PDF 图像提取整体失败 (%s): %s", path, exc)
        return []

    return images


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------

def _parse_docx(path: Path) -> dict[str, Any]:
    try:
        from docx import Document  # type: ignore[import-untyped]
    except ImportError:
        raise ImportError("Install python-docx: pip install python-docx") from None

    doc = Document(path)

    author = doc.core_properties.author
    metadata = {
        "format": "docx",
        "title": doc.core_properties.title or "",
        "authors": [author] if author else [],
        "has_abstract": False,
        "page_count": 1,  # DOCX doesn't have precise page count
        "file_size_bytes": path.stat().st_size,
    }

    segments: list[dict[str, Any]] = []
    current_type = "body"
    full_text_parts: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        full_text_parts.append(text)

        # Check if this is a heading that marks a section
        detected = _detect_section(text)
        if detected is not None:
            current_type = detected

        segments.append({
            "type": current_type,
            "text": text[:5000],
            "page_start": 1,
            "page_end": 1,
            "confidence": 0.8,
        })

    # Update has_abstract from content
    full_text = "\n".join(full_text_parts)
    metadata["has_abstract"] = bool(re.search(r"(?i)abstract", full_text))

    # Fill title from first line if core_properties.title is empty
    if not metadata["title"]:
        metadata["title"] = _extract_title_from_text(full_text)

    return {
        "metadata": metadata,
        "segments": segments,
        "images": [],
        "tables": [],
        "declarations": {},
    }


# ---------------------------------------------------------------------------
# LaTeX (.tex)
# ---------------------------------------------------------------------------

_TEX_SECTION_PATTERNS: dict[str, re.Pattern] = {
    "abstract": re.compile(r"\\begin\{abstract\}"),
    "introduction": re.compile(r"\\section\{[^}]*[Ii]ntroduction"),
    "methods": re.compile(r"\\section\{[^}]*[Mm]ethod"),
    "results": re.compile(r"\\section\{[^}]*[Rr]esult"),
    "discussion": re.compile(r"\\section\{[^}]*[Dd]iscussion"),
    "conclusion": re.compile(r"\\section\{[^}]*[Cc]onclusion"),
    "references": re.compile(r"\\section\{[^}]*[Rr]eference"),
}


def _extract_tex_title(text: str) -> str:
    match = re.search(r"\\title\{([^}]+)\}", text)
    return match.group(1).strip() if match else "Untitled"


def _extract_tex_authors(text: str) -> list[str]:
    match = re.search(r"\\author\{([^}]+)\}", text)
    if match:
        raw = match.group(1)
        # Handle "and" separated author list, strip LaTeX commands
        authors = [re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "", a).strip() for a in raw.split(" and ")]
        return [a for a in authors if a]
    return []


def _strip_latex(text: str) -> str:
    """Remove common LaTeX commands and braces for clean text output.

    Handles nested commands like ``\\textbf{\\textit{nested}}`` by repeatedly
    applying the strip regex until no more matches remain (max 5 iterations).
    """
    brace_re = re.compile(r"\\[a-zA-Z]+\{([^{}]*)\}")
    for _ in range(5):
        new = brace_re.sub(r"\1", text)
        if new == text:
            break
        text = new
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = text.replace("~", " ")
    return text.strip()


def _parse_tex(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")

    metadata = {
        "format": "tex",
        "title": _extract_tex_title(text),
        "authors": _extract_tex_authors(text),
        "has_abstract": bool(re.search(r"\\begin\{abstract\}", text)),
        "page_count": 1,
        "file_size_bytes": path.stat().st_size,
    }

    # Split into paragraphs and classify
    current_type = "body"
    segments: list[dict[str, Any]] = []

    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue

        for stype, pat in _TEX_SECTION_PATTERNS.items():
            if pat.search(para):
                current_type = stype
                break

        clean = _strip_latex(para)
        if len(clean) > 10:
            segments.append({
                "type": current_type,
                "text": clean[:5000],
                "page_start": 1,
                "page_end": 1,
                "confidence": 0.6,
            })

    return {
        "metadata": metadata,
        "segments": segments,
        "images": [],
        "tables": [],
        "declarations": {},
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _cli_parser = argparse.ArgumentParser(
        description="解析论文文件（PDF/DOCX/TXT/TEX），输出结构化 JSON",
    )
    _cli_parser.add_argument("paper_file", help="论文文件路径")
    _cli_parser.add_argument(
        "--images",
        action="store_true",
        help="提取 PDF 页面图像为 base64（较慢，仅 PDF 有效）",
    )
    _cli_args = _cli_parser.parse_args()

    result = parse_paper(_cli_args.paper_file)

    if _cli_args.images and result["metadata"]["format"] == "pdf":
        page_images = _extract_pdf_page_images(Path(_cli_args.paper_file))
        result["images"] = page_images

    print(json.dumps(result, ensure_ascii=False, indent=2))
