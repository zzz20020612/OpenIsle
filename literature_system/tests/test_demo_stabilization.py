from __future__ import annotations

import json
import sys
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parents[1] / "code"
SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
for root in (CODE_ROOT, SCRIPTS_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

import demo_stabilization
from demo_stabilization import build_report, choose_retry_ids, write_reports


def sample_audit():
    return {
        1: {"state": "complete", "retryable": False, "reason_codes": []},
        2: {"state": "retryable", "retryable": True, "reason_codes": ["pdf_not_downloaded"]},
        3: {"state": "incomplete", "retryable": True, "reason_codes": ["fulltext_too_short"]},
        4: {"state": "terminal", "retryable": False, "reason_codes": ["paywalled"]},
    }


def test_retry_selection_is_bounded_and_excludes_complete_and_terminal():
    assert choose_retry_ids(sample_audit(), limit=1) == [2]
    assert choose_retry_ids(sample_audit(), limit=10) == [2, 3]


def test_report_counts_states_and_failure_reasons():
    report = build_report(sample_audit(), target=30, rounds=2, attempts=[{"topic": "climate"}])

    assert report["target_complete"] == 30
    assert report["complete_count"] == 1
    assert report["target_reached"] is False
    assert report["states"] == {
        "complete": 1, "retryable": 1, "incomplete": 1, "terminal": 1
    }
    assert report["failure_reasons"]["paywalled"] == 1


def test_reports_are_written_as_json_and_markdown(tmp_path):
    report = build_report(sample_audit(), target=1, rounds=1, attempts=[])

    json_path, markdown_path = write_reports(report, tmp_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["target_reached"] is True
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Complete papers | 1" in markdown
    assert "paywalled | 1" in markdown


def test_stabilize_retries_then_collects_and_stops_at_target(monkeypatch):
    audits = iter([
        {2: {"state": "retryable", "retryable": True, "stage": "pdf"}},
        {2: {"state": "retryable", "retryable": True, "stage": "pdf"}},
        {1: {"state": "complete", "complete": True, "retryable": False}},
    ])
    calls = []
    monkeypatch.setattr(demo_stabilization, "audit_corpus", lambda: next(audits))
    monkeypatch.setattr(
        demo_stabilization,
        "_retry",
        lambda proxy, paper_id, stage: calls.append(("retry", paper_id, stage)) or {"ok": True},
    )
    monkeypatch.setattr(
        demo_stabilization,
        "_collect_process",
        lambda proxy, topic, source, size: calls.append(("collect", topic, source, size)) or {"ok": True},
    )

    report = demo_stabilization.stabilize(
        target=1,
        topics=("climate",),
        sources=("arxiv",),
        batch_size=5,
        max_rounds=3,
        retry_limit=2,
    )

    assert calls == [("retry", 2, "pdf"), ("collect", "climate", "arxiv", 5)]
    assert report["target_reached"] is True
    assert report["rounds"] == 1
