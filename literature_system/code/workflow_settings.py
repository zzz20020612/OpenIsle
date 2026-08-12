"""工作流配置管理。

将部分原本只能通过 .env 修改的参数暴露到数据库，支持前端 UI 动态配置。
读取时以数据库为准，缺失的键使用 config 模块默认值。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config
from db import get_connection


def _default_settings() -> Dict[str, Any]:
    """与 config.py 保持一致的默认配置。"""
    return {
        # 采集源
        "collect_sources": ["crossref"],
        # API keys
        "semantic_scholar_api_key": config.SEMANTIC_SCHOLAR_API_KEY,
        "mineru_api_key": config.MINERU_API_KEY,
        "llm_api_key": config.LLM_API_KEY,
        "embedding_api_key": config.EMBEDDING_API_KEY,
        "wos_api_key": config.WOS_API_KEY,
        "scopus_api_keys": ",".join(config.SCOPUS_API_KEYS),
        # PDF 下载策略（数字越小优先级越高，0=禁用）
        "pdf_strategy_crossref_text_mining": config.PDF_DOWNLOAD_STRATEGY.get("crossref_text_mining", 1),
        "pdf_strategy_crossref_pdf": config.PDF_DOWNLOAD_STRATEGY.get("crossref_pdf", 2),
        "pdf_strategy_oa_url": config.PDF_DOWNLOAD_STRATEGY.get("oa_url", 3),
        "pdf_strategy_doi_redirect": config.PDF_DOWNLOAD_STRATEGY.get("doi_redirect", 4),
        "pdf_strategy_unpaywall": config.PDF_DOWNLOAD_STRATEGY.get("unpaywall", 5),
        # PDF 解析策略
        "pdf_parser_mineru_api": config.PDF_PARSER_STRATEGY.get("mineru_api", 1),
        "pdf_parser_pymupdf": config.PDF_PARSER_STRATEGY.get("pymupdf", 2),
        "pdf_parser_marker_gpu": config.PDF_PARSER_STRATEGY.get("marker_gpu", 3),
        "pdf_parser_marker_cpu": config.PDF_PARSER_STRATEGY.get("marker_cpu", 4),
        # LLM 提炼参数
        "llm_base_url": config.LLM_BASE_URL,
        "llm_model": config.LLM_MODEL,
        "llm_max_tokens": config.LLM_MAX_TOKENS,
        "llm_temperature": config.LLM_TEMPERATURE,
        "llm_request_timeout": config.LLM_REQUEST_TIMEOUT,
        "llm_max_retries": config.LLM_MAX_RETRIES,
        # Embedding 参数
        "embedding_base_url": config.EMBEDDING_BASE_URL,
        "embedding_model": config.EMBEDDING_MODEL,
        "embedding_dim": config.EMBEDDING_DIM,
        "embedding_batch_size": config.EMBEDDING_BATCH_SIZE,
    }


def _serialize(value: Any) -> str:
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _deserialize(raw: str, key: str) -> Any:
    defaults = _default_settings()
    default = defaults.get(key)
    if isinstance(default, list):
        try:
            return json.loads(raw)
        except Exception:
            return raw.split(",") if raw else []
    if isinstance(default, bool):
        return raw.lower() in ("true", "1", "t")
    if isinstance(default, int):
        try:
            return int(raw)
        except ValueError:
            return default
    if isinstance(default, float):
        try:
            return float(raw)
        except ValueError:
            return default
    return raw


# 敏感 key：返回时脱敏，避免接口泄露
SENSITIVE_KEYS = {
    "semantic_scholar_api_key",
    "mineru_api_key",
    "llm_api_key",
    "embedding_api_key",
    "wos_api_key",
    "scopus_api_keys",
}


def _mask_value(value: str) -> str:
    """对密钥类字符串脱敏，只保留前 4 位。"""
    if not value or len(value) <= 4:
        return value
    return value[:4] + "*" * (len(value) - 4)


def get_settings(conn=None, mask_sensitive: bool = False) -> Dict[str, Any]:
    """读取工作流配置，缺失键使用默认值填充。

    Args:
        mask_sensitive: 为 True 时对 SENSITIVE_KEYS 中的值进行脱敏。
    """
    close_conn = conn is None
    if conn is None:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM workflow_settings")
    stored = {row[0]: row[1] for row in cur.fetchall()}
    if close_conn:
        conn.close()

    merged = _default_settings()
    for key, raw in stored.items():
        merged[key] = _deserialize(raw, key)

    if mask_sensitive:
        for key in SENSITIVE_KEYS:
            if key in merged and merged[key]:
                merged[key] = _mask_value(str(merged[key]))
    return merged


def _is_masked(value: Any) -> bool:
    """判断前端提交的值是否为脱敏占位符（如 sk-vn********）。"""
    if not isinstance(value, str) or len(value) <= 4:
        return False
    # 脱敏值特征：前 4 位后是连续的 *，且 * 占比高
    tail = value[4:]
    return tail and tail.count("*") == len(tail)


def set_settings(updates: Dict[str, Any], conn=None) -> Dict[str, Any]:
    """保存工作流配置。

    对敏感 key，如果提交的值仍是脱敏占位符，则跳过更新，避免把 mask 字符串存入库。
    """
    close_conn = conn is None
    if conn is None:
        conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    for key, value in updates.items():
        if key in SENSITIVE_KEYS and _is_masked(value):
            continue
        raw = _serialize(value)
        cur.execute(
            "INSERT INTO workflow_settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, raw, now),
        )
    conn.commit()
    if close_conn:
        conn.close()
    return get_settings(mask_sensitive=True)


def apply_to_config() -> None:
    """将数据库中的工作流配置写入当前进程 config 模块（用于任务运行时覆盖）。"""
    settings = get_settings()
    config.SEMANTIC_SCHOLAR_API_KEY = settings.get("semantic_scholar_api_key", "")
    config.MINERU_API_KEY = settings.get("mineru_api_key", "")
    # An empty historical database value must not hide the shared OpenIsle
    # screening credential loaded from the environment.
    config.LLM_API_KEY = settings.get("llm_api_key") or config.LLM_API_KEY
    config.EMBEDDING_API_KEY = settings.get("embedding_api_key", "")
    config.WOS_API_KEY = settings.get("wos_api_key", "")
    config.SCOPUS_API_KEYS = [k.strip() for k in settings.get("scopus_api_keys", "").split(",") if k.strip()]

    config.PDF_DOWNLOAD_STRATEGY = {
        "crossref_text_mining": int(settings.get("pdf_strategy_crossref_text_mining", 1)),
        "crossref_pdf": int(settings.get("pdf_strategy_crossref_pdf", 2)),
        "oa_url": int(settings.get("pdf_strategy_oa_url", 3)),
        "doi_redirect": int(settings.get("pdf_strategy_doi_redirect", 4)),
        "unpaywall": int(settings.get("pdf_strategy_unpaywall", 5)),
    }
    config.PDF_PARSER_STRATEGY = {
        "mineru_api": int(settings.get("pdf_parser_mineru_api", 1)),
        "pymupdf": int(settings.get("pdf_parser_pymupdf", 2)),
        "marker_gpu": int(settings.get("pdf_parser_marker_gpu", 3)),
        "marker_cpu": int(settings.get("pdf_parser_marker_cpu", 4)),
    }

    config.LLM_BASE_URL = settings.get("llm_base_url") or config.LLM_BASE_URL
    config.LLM_MODEL = settings.get("llm_model") or config.LLM_MODEL
    config.LLM_MAX_TOKENS = int(settings.get("llm_max_tokens", config.LLM_MAX_TOKENS))
    config.LLM_TEMPERATURE = float(settings.get("llm_temperature", config.LLM_TEMPERATURE))
    config.LLM_REQUEST_TIMEOUT = int(settings.get("llm_request_timeout", config.LLM_REQUEST_TIMEOUT))
    config.LLM_MAX_RETRIES = int(settings.get("llm_max_retries", config.LLM_MAX_RETRIES))

    config.EMBEDDING_BASE_URL = settings.get("embedding_base_url", config.EMBEDDING_BASE_URL)
    config.EMBEDDING_MODEL = settings.get("embedding_model", config.EMBEDDING_MODEL)
    config.EMBEDDING_DIM = int(settings.get("embedding_dim", config.EMBEDDING_DIM))
    config.EMBEDDING_BATCH_SIZE = int(settings.get("embedding_batch_size", config.EMBEDDING_BATCH_SIZE))
