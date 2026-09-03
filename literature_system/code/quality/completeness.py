"""Stable completeness contract for the existing-literature demo corpus."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping


MIN_FULLTEXT_CHARS = 2_000

REASON_MESSAGES = {
    "missing_title": "The source metadata does not contain a title.",
    "missing_author": "The source metadata does not contain author information.",
    "no_pdf_locator": "No DOI or open-PDF location is available.",
    "pdf_not_downloaded": "An open PDF still needs to be downloaded.",
    "paywalled": "The available full text requires paid access.",
    "invalid_pdf": "The downloaded payload is not a valid PDF.",
    "paper_mismatch": "The downloaded PDF does not match the literature record.",
    "fulltext_missing": "The PDF has not produced parsed full text.",
    "fulltext_too_short": "Parsed full text is too short for a reliable demonstration.",
    "sections_missing": "No substantive document sections were parsed.",
    "knowledge_missing": "The knowledge card has not been extracted.",
    "methods_missing": "The methods record has not been extracted.",
    "data_extraction_incomplete": "Data-point extraction has not reached a terminal successful state.",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _terminal_reason(job: Mapping[str, Any]) -> str | None:
    error_class = _text(job.get("error_class")).lower()
    message = _text(job.get("error_msg") or job.get("message")).lower()
    combined = f"{error_class} {message}"
    if any(token in combined for token in ("paywall", "requires payment", "paid access")):
        return "paywalled"
    if any(token in combined for token in ("invalidpdf", "invalid_pdf", "not a pdf")):
        return "invalid_pdf"
    if any(token in combined for token in ("papermismatch", "paper_mismatch", "does not match")):
        return "paper_mismatch"
    return None


def _result(
    state: str,
    stage: str,
    reasons: list[str],
    *,
    retryable: bool,
    evidence: Dict[str, Any],
) -> Dict[str, Any]:
    level = evidence["level"]
    return {
        "state": state,
        "stage": stage,
        "complete": state == "complete" and level == "L4",
        "level": level,
        "level_label": evidence["level_label"],
        "usable": level in {"L2", "L3", "L4"},
        "evaluable": state == "complete" and level == "L4",
        "visual_content_extracted": evidence["figure_count"] > 0,
        "warnings": [] if evidence["figure_count"] > 0 else ["visual_content_missing"],
        "retryable": retryable,
        "reason_codes": reasons,
        "reasons": [REASON_MESSAGES[reason] for reason in reasons],
        "evidence": evidence,
    }


def assess_completeness(values: Mapping[str, Any]) -> Dict[str, Any]:
    """Classify one paper using observable persisted artifacts.

    The result intentionally distinguishes retriable processing gaps from
    terminal source limitations.  It is shared by the API, batch runner and
    final demonstration report so those surfaces cannot disagree about which
    papers count toward the complete corpus.
    """
    char_count = int(values.get("fulltext_char_count") or 0)
    section_count = int(values.get("section_count") or 0)
    figure_count = int(values.get("figure_count") or 0)
    data_status = _text(values.get("data_extraction_status")).lower()
    pdf_available = bool(values.get("pdf_available"))
    parsed = char_count >= MIN_FULLTEXT_CHARS and section_count > 0
    knowledge_ready = bool(values.get("knowledge_present")) and bool(values.get("methods_present"))
    data_ready = data_status in {"done", "skipped"}
    # The L0-L4 level describes processing artifacts only. Metadata quality is
    # reported independently through `state` and reason codes, so a missing
    # author cannot falsely hide an already parsed PDF as L0.
    if not pdf_available:
        level = "L0"
    elif not parsed:
        level = "L1"
    elif not knowledge_ready:
        level = "L2"
    elif not data_ready:
        level = "L3"
    else:
        level = "L4"
    level_labels = {
        "L0": "Metadata only",
        "L1": "PDF ready",
        "L2": "Full text parsed",
        "L3": "Knowledge extracted",
        "L4": "Ready for evaluation",
    }
    evidence = {
        "pdf_available": pdf_available,
        "fulltext_char_count": char_count,
        "section_count": section_count,
        "knowledge_present": bool(values.get("knowledge_present")),
        "methods_present": bool(values.get("methods_present")),
        "data_extraction_status": data_status or None,
        "figure_count": figure_count,
        "level": level,
        "level_label": level_labels[level],
    }

    metadata_reasons = []
    if not _text(values.get("title")):
        metadata_reasons.append("missing_title")
    if not _text(values.get("author")):
        metadata_reasons.append("missing_author")
    if metadata_reasons:
        return _result(
            "incomplete", "metadata", metadata_reasons,
            retryable=False, evidence=evidence,
        )

    latest_job = values.get("latest_job") or {}
    job_status = _text(latest_job.get("status")).lower()
    job_stage = _text(latest_job.get("stage")) or "processing"
    if job_status in {"pending", "running"}:
        return _result(
            "processing", job_stage, [], retryable=False, evidence=evidence
        )

    terminal_reason = _terminal_reason(latest_job)
    if terminal_reason:
        return _result(
            "terminal", job_stage, [terminal_reason],
            retryable=False, evidence=evidence,
        )

    if not evidence["pdf_available"]:
        if not _text(values.get("doi")) and not _text(values.get("oa_url")):
            return _result(
                "terminal", "pdf", ["no_pdf_locator"],
                retryable=False, evidence=evidence,
            )
        return _result(
            "retryable", "pdf", ["pdf_not_downloaded"],
            retryable=True, evidence=evidence,
        )

    if char_count <= 0:
        return _result(
            "retryable", "parse", ["fulltext_missing"],
            retryable=True, evidence=evidence,
        )
    if char_count < MIN_FULLTEXT_CHARS:
        return _result(
            "incomplete", "parse", ["fulltext_too_short"],
            retryable=True, evidence=evidence,
        )
    if section_count <= 0:
        return _result(
            "incomplete", "parse", ["sections_missing"],
            retryable=True, evidence=evidence,
        )

    extraction_reasons = []
    if not evidence["knowledge_present"]:
        extraction_reasons.append("knowledge_missing")
    if not evidence["methods_present"]:
        extraction_reasons.append("methods_missing")
    if extraction_reasons:
        return _result(
            "retryable", "extract", extraction_reasons,
            retryable=True, evidence=evidence,
        )

    if not data_ready:
        return _result(
            "retryable", "extract", ["data_extraction_incomplete"],
            retryable=True, evidence=evidence,
        )

    return _result("complete", "complete", [], retryable=False, evidence=evidence)


def load_completeness_many(
    conn: Any,
    paper_ids: Iterable[int],
    pdf_available_by_id: Mapping[int, bool],
) -> Dict[int, Dict[str, Any]]:
    """Load and classify multiple papers with one aggregate database query."""
    ids = list(dict.fromkeys(int(paper_id) for paper_id in paper_ids))
    if not ids:
        return {}

    placeholders = ",".join("?" for _ in ids)
    sql = f"""
        SELECT p.id, p.doi, p.title, p.author, p.oa_url,
               COALESCE(ft.char_count, 0) AS fulltext_char_count,
               COUNT(DISTINCT s.id) AS section_count,
               CASE WHEN kc.paper_id IS NULL THEN 0 ELSE 1 END AS knowledge_present,
               CASE WHEN pm.paper_id IS NULL THEN 0 ELSE 1 END AS methods_present,
               COUNT(DISTINCT pf.id) AS figure_count,
               dj.status AS data_extraction_status,
               j.stage AS job_stage, j.status AS job_status,
               j.error_class AS job_error_class, j.error_msg AS job_error_msg
        FROM papers p
        LEFT JOIN paper_fulltext ft ON ft.paper_id = p.id
        LEFT JOIN paper_sections s ON s.paper_id = p.id
        LEFT JOIN paper_knowledge_cards kc ON kc.paper_id = p.id
        LEFT JOIN paper_methods pm ON pm.paper_id = p.id
        LEFT JOIN paper_figures pf ON pf.paper_id = p.id
        LEFT JOIN parse_jobs dj ON dj.id = (
            SELECT dj2.id FROM parse_jobs dj2
            WHERE dj2.paper_id = p.id AND dj2.stage = 'extract'
              AND dj2.parser_used = 'data_points'
            ORDER BY dj2.id DESC LIMIT 1
        )
        LEFT JOIN parse_jobs j ON j.id = (
            SELECT j2.id FROM parse_jobs j2
            WHERE j2.paper_id = p.id
            ORDER BY j2.id DESC LIMIT 1
        )
        WHERE p.id IN ({placeholders})
        GROUP BY p.id, p.doi, p.title, p.author, p.oa_url,
                 ft.char_count, kc.paper_id, pm.paper_id, dj.status,
                 j.stage, j.status, j.error_class, j.error_msg
    """
    cur = conn.cursor()
    cur.execute(sql, ids)
    results: Dict[int, Dict[str, Any]] = {}
    for row in cur.fetchall():
        values = dict(row)
        paper_id = int(values.pop("id"))
        job_status = values.pop("job_status")
        values["latest_job"] = None if not job_status else {
            "stage": values.pop("job_stage"),
            "status": job_status,
            "error_class": values.pop("job_error_class"),
            "error_msg": values.pop("job_error_msg"),
        }
        if not job_status:
            values.pop("job_stage")
            values.pop("job_error_class")
            values.pop("job_error_msg")
        values["pdf_available"] = bool(pdf_available_by_id.get(paper_id))
        results[paper_id] = assess_completeness(values)
    return results
