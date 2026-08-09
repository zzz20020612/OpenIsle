"""
scansci-pdf 白源桥接层

通过 scansci-pdf 的合法开放获取来源（Unpaywall、OpenAlex、CORE、Europe PMC、
Semantic Scholar、OA 出版商等）解析并下载 PDF。默认不启用 Sci-Hub、LibGen、
浏览器模拟、机构 VPN 等灰色或重量级来源。

使用方式：
    result = try_download(doi, oa_url=oa_url, output_path=path)
    if result["success"]:
        print(result["file_path"], result["source"], result["size_kb"])
"""
from __future__ import annotations

import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# 添加项目根目录，确保能 import code.config
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config

_import_err_msg = ""

# 来源名称 -> 处理函数（publishers 特殊处理）
_SOURCE_FUNCS: dict[str, Any] = {}

# 分层竞争：先跑 Tier 1（repository / 聚合索引），再跑 Tier 2（索引 / 出版商）
_TIER1_SOURCES = ["unpaywall", "openalex_oa", "core", "europepmc", "pmc"]
_TIER2_SOURCES = ["semanticscholar", "arxiv", "publishers"]

try:
    from scansci_pdf.pdf_utils import download_pdf, is_plausible_pdf_url
    from scansci_pdf.sources import (
        try_arxiv,
        try_core,
        try_europepmc,
        try_openalex_content_api,
        try_openalex_oa,
        try_pmc,
        try_semanticscholar,
        try_unpaywall,
        get_publisher_fast_sources,
    )

    _SOURCE_FUNCS = {
        "arxiv": try_arxiv,
        "core": try_core,
        "europepmc": try_europepmc,
        "pmc": try_pmc,
        "openalex_oa": try_openalex_oa,
        "openalex_content": try_openalex_content_api,
        "unpaywall": try_unpaywall,
        "semanticscholar": try_semanticscholar,
    }
    _HAS_SCISCI = True
except Exception as _import_err:  # pragma: no cover
    _HAS_SCISCI = False
    _import_err_msg = str(_import_err)


def _source_enabled(source: str) -> bool:
    """检查来源是否在白名单中。"""
    whitelist = getattr(config, "PDF_SOURCE_WHITELIST", "")
    if not whitelist:
        return False
    enabled = {s.strip().lower() for s in str(whitelist).split(",") if s.strip()}
    return source.lower() in enabled


def _build_config() -> dict[str, Any]:
    """构建传给 scansci-pdf 的最小配置。"""
    return {
        "email": getattr(config, "CROSSREF_MAILTO", "") or "research@example.com",
        "connect_timeout": int(getattr(config, "PDF_SOURCE_CONNECT_TIMEOUT", "10")),
        "read_timeout": int(getattr(config, "PDF_SOURCE_READ_TIMEOUT", "20")),
        "request_delay_min": 0.0,
        "request_delay_max": 0.0,
        "fixed_request_delay_enabled": False,  # 关闭礼貌延迟，避免并发被拖慢
        "min_pdf_size_bytes": 10000,
        "network_proxy": getattr(config, "NETWORK_PROXY", ""),
        "openalex_api_key": getattr(config, "OPENALEX_API_KEY", ""),
        "core_api_key": getattr(config, "CORE_API_KEY", ""),
        "parallel_sources": True,
    }


def _safe_doi_filename(doi: str) -> str:
    """生成 Windows 安全的文件名前缀。"""
    return (
        doi.replace("/", "_")
        .replace(":", "_")
        .replace("\\", "_")
        .replace("?", "_")
        .replace("*", "_")
        .replace('"', "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("|", "_")[:120]
    )


def _resolve_output_path(output_path: Path | str | None, doi: str) -> Path:
    """确定输出文件路径。"""
    if output_path is not None:
        return Path(output_path)
    tmp_dir = Path(tempfile.gettempdir()) / "scansci_bridge"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir / f"{_safe_doi_filename(doi)}.pdf"


def _try_oa_url(oa_url: str, output_path: Path, cfg: dict[str, Any]) -> dict[str, Any] | None:
    """优先验证调用方传入的 oa_url。"""
    if not oa_url or not is_plausible_pdf_url(oa_url):
        return None
    return download_pdf(oa_url, output_path, cfg, "oa_url")


def _try_source(source: str, doi: str, output_path: Path, cfg: dict[str, Any]) -> dict[str, Any] | None:
    """调用单个来源的下载函数。"""
    try:
        if source == "publishers":
            return _try_publishers(doi, output_path, cfg)

        func = _SOURCE_FUNCS.get(source)
        if func is None:
            return None
        return func(doi, output_path, cfg)
    except Exception:
        return None


def _try_publishers(doi: str, output_path: Path, cfg: dict[str, Any]) -> dict[str, Any] | None:
    """调用 scansci-pdf 的出版商快速通道（仅 OA 出版商）。"""
    try:
        sources = get_publisher_fast_sources(doi)
        if not sources:
            return None
        for func, tool_name in sources:
            try:
                res = func(doi, output_path, cfg)
                if res and res.get("success"):
                    res["source"] = tool_name
                    return res
            except Exception:
                continue
    except Exception:
        pass
    return None


def _run_tier(
    doi: str,
    sources: list[str],
    output_path: Path,
    cfg: dict[str, Any],
    timeout: float,
) -> dict[str, Any] | None:
    """并发执行一层来源，取最快成功结果。"""
    if not sources:
        return None

    start = time.time()
    max_workers = min(len(sources), int(getattr(config, "PDF_TIER1_WORKERS", "5")))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_try_source, s, doi, output_path, cfg): s for s in sources}
        for future in as_completed(futures):
            if time.time() - start > timeout:
                break
            try:
                res = future.result()
                if res and res.get("success"):
                    return {
                        "file_path": str(output_path),
                        "source": res.get("source", futures[future]),
                        "size_kb": res.get("size_kb"),
                    }
            except Exception:
                continue
    return None


def try_download(
    doi: str,
    oa_url: str | None = None,
    output_path: Path | str | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    使用 scansci-pdf 白源尝试下载 PDF。

    Args:
        doi: DOI 标识符
        oa_url: 调用方已知的 OA URL，优先验证
        output_path: PDF 保存路径，默认写入临时目录
        timeout: 整层竞争超时（秒）

    Returns:
        {
            "success": bool,
            "file_path": str | None,
            "source": str | None,
            "size_kb": float | None,
            "error": str | None,
            "error_class": str | None,
        }
    """
    # 开关检查
    if not _HAS_SCISCI:
        return {
            "success": False,
            "file_path": None,
            "source": None,
            "size_kb": None,
            "error": f"scansci-pdf 未安装: {_import_err_msg}",
            "error_class": "scansci_import_error",
        }

    if not getattr(config, "PDF_ENABLE_SCISCI", False):
        return {
            "success": False,
            "file_path": None,
            "source": None,
            "size_kb": None,
            "error": "scansci-pdf 桥接已禁用",
            "error_class": "scansci_disabled",
        }

    if not doi:
        return {
            "success": False,
            "file_path": None,
            "source": None,
            "size_kb": None,
            "error": "DOI 为空",
            "error_class": "invalid_doi",
        }

    cfg = _build_config()
    output_path = _resolve_output_path(output_path, doi)

    # 1. oa_url 快速通道
    if oa_url and _source_enabled("oa_url"):
        res = _try_oa_url(oa_url, output_path, cfg)
        if res and res.get("success"):
            return {
                "success": True,
                "file_path": str(output_path),
                "source": "oa_url",
                "size_kb": res.get("size_kb"),
                "error": None,
                "error_class": None,
            }

    # 2. Tier 1 并发竞争
    tier1 = [s for s in _TIER1_SOURCES if _source_enabled(s)]
    tier1_result = _run_tier(doi, tier1, output_path, cfg, timeout)
    if tier1_result:
        return {
            "success": True,
            "file_path": tier1_result["file_path"],
            "source": tier1_result["source"],
            "size_kb": tier1_result["size_kb"],
            "error": None,
            "error_class": None,
        }

    # 3. Tier 2 并发竞争
    tier2 = [s for s in _TIER2_SOURCES if _source_enabled(s)]
    tier2_result = _run_tier(doi, tier2, output_path, cfg, timeout)
    if tier2_result:
        return {
            "success": True,
            "file_path": tier2_result["file_path"],
            "source": tier2_result["source"],
            "size_kb": tier2_result["size_kb"],
            "error": None,
            "error_class": None,
        }

    # 4. OpenAlex Content API（需要 API Key）
    if _source_enabled("openalex_content") and cfg.get("openalex_api_key"):
        res = _try_source("openalex_content", doi, output_path, cfg)
        if res and res.get("success"):
            return {
                "success": True,
                "file_path": str(output_path),
                "source": res.get("source", "openalex_content"),
                "size_kb": res.get("size_kb"),
                "error": None,
                "error_class": None,
            }

    return {
        "success": False,
        "file_path": None,
        "source": None,
        "size_kb": None,
        "error": "所有白源均未找到可下载 PDF",
        "error_class": "no_oa_version",
    }


def resolve_pdf_url(
    doi: str,
    oa_url: str | None = None,
    timeout: float = 30.0,
) -> tuple[str | None, str | None]:
    """
    兼容旧接口的包装：尝试下载到临时文件，成功后返回该临时文件路径与来源。

    注意：scansci-pdf 的 try_* 函数会直接下载 PDF 并验证，因此这里返回的是
    已验证的本地文件路径，调用方可直接复制或移动。

    Returns:
        (pdf_path_or_url, source_name)
    """
    result = try_download(doi, oa_url=oa_url, timeout=timeout)
    if result["success"]:
        return result["file_path"], result["source"]
    return None, None
