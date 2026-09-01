"""Runtime capability audit for the restored literature engine.

This module reports what can actually execute in the current environment.
Source files or configured priorities alone are not treated as evidence that a
parser, model, or provider is operational.
"""
from __future__ import annotations

import importlib.util
import shutil
from typing import Any, Dict

import config


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def get_engine_capabilities() -> Dict[str, Any]:
    dependencies = {
        "requests": _module_available("requests"),
        "dotenv": _module_available("dotenv"),
        "pymupdf": _module_available("fitz"),
        "sqlite_vec": _module_available("sqlite_vec"),
        "numpy": _module_available("numpy"),
        "html2text": _module_available("html2text"),
    }

    parsers = {
        "mineru_api": {
            "configured": bool(config.MINERU_API_KEY),
            "implemented": True,
            "priority": config.PDF_PARSER_STRATEGY.get("mineru_api", 0),
        },
        "pymupdf": {
            "configured": dependencies["pymupdf"],
            "implemented": True,
            "priority": config.PDF_PARSER_STRATEGY.get("pymupdf", 0),
        },
        # The teammate source advertises Marker in the fallback order, but its
        # pipeline explicitly skips both branches. Report that fact instead of
        # claiming a configured priority is a working parser.
        "marker_gpu": {
            "configured": shutil.which("marker_single") is not None,
            "implemented": False,
            "priority": config.PDF_PARSER_STRATEGY.get("marker_gpu", 0),
        },
        "marker_cpu": {
            "configured": shutil.which("marker_single") is not None,
            "implemented": False,
            "priority": config.PDF_PARSER_STRATEGY.get("marker_cpu", 0),
        },
    }

    models = {
        "llm": {
            "configured": bool(config.LLM_API_KEY),
            "base_url": config.LLM_BASE_URL,
            "model": config.LLM_MODEL,
        },
        "embedding": {
            "configured": bool(config.EMBEDDING_API_KEY),
            "base_url": config.EMBEDDING_BASE_URL,
            "model": config.EMBEDDING_MODEL,
            "dimension": config.EMBEDDING_DIM,
        },
    }

    sources = {
        "crossref": {"configured": True, "requires_key": False},
        "arxiv": {"configured": True, "requires_key": False},
        "pmc": {"configured": True, "requires_key": False},
        "pubmed": {"configured": True, "requires_key": False},
        "openalex": {"configured": True, "requires_key": False},
        "unpaywall": {"configured": bool(config.UNPAYWALL_EMAIL), "requires_key": False},
        "semantic_scholar": {
            "configured": bool(config.SEMANTIC_SCHOLAR_API_KEY),
            "requires_key": False,
            "anonymous_fallback": True,
        },
        "web_of_science": {"configured": bool(config.WOS_API_KEY), "requires_key": True},
        "scopus": {"configured": bool(config.SCOPUS_API_KEYS), "requires_key": True},
    }

    # sqlite-vec only affects semantic/vector retrieval. The ordinary corpus,
    # PDF, extraction, keyword-search and graph workflows remain operational
    # through SQLite and the NumPy fallback, so it must not mark the complete
    # non-vector runtime as unavailable.
    core_dependencies = ("requests", "dotenv", "pymupdf", "numpy", "html2text")
    missing_required = [name for name in core_dependencies if not dependencies[name]]
    missing_full_restore = list(missing_required)
    if not dependencies["sqlite_vec"]:
        missing_full_restore.append("sqlite_vec")
    if not parsers["mineru_api"]["configured"]:
        missing_full_restore.append("MINERU_API_KEY")
    if not models["llm"]["configured"]:
        missing_full_restore.append("LLM_API_KEY")
    if not models["embedding"]["configured"]:
        missing_full_restore.append("EMBEDDING_API_KEY")
    original_source_limitations = []
    if not parsers["marker_gpu"]["implemented"]:
        original_source_limitations.append("marker_parser_not_implemented_in_original_source")

    return {
        "engine": "scholar-literature-system",
        "runtime_ready": not missing_required and models["llm"]["configured"],
        "full_restore_ready": not missing_full_restore,
        "missing_required": missing_required,
        "missing_full_restore": missing_full_restore,
        "original_source_limitations": original_source_limitations,
        "dependencies": dependencies,
        "parsers": parsers,
        "models": models,
        "sources": sources,
    }
