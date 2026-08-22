"""Build and audit a resumable open-literature demonstration corpus."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from db import get_connection
from pdf.pipeline import get_pdf_path
from quality.completeness import load_completeness_many


DEFAULT_TOPICS = (
    "climate adaptation",
    "renewable energy",
    "biodiversity conservation",
    "environmental pollution",
)
DEFAULT_SOURCES = ("arxiv", "pmc")


class ConsoleProgress:
    def set_progress(self, percent: int, message: str) -> None:
        print(f"[{percent:3d}%] {message}", flush=True)


def audit_corpus() -> dict[int, dict[str, Any]]:
    """Audit every non-placeholder record using persisted artifacts."""
    with get_connection(init_schema=False, row_factory=True) as conn:
        rows = conn.execute(
            "SELECT id, doi FROM papers WHERE COALESCE(is_placeholder, 0) = 0 ORDER BY id"
        ).fetchall()
        pdfs = {
            int(row["id"]): bool(get_pdf_path(int(row["id"]), row["doi"]))
            for row in rows
        }
        return load_completeness_many(conn, pdfs.keys(), pdfs)


def choose_retry_ids(
    audit: Mapping[int, Mapping[str, Any]], limit: int, excluded: set[int] | None = None
) -> list[int]:
    """Choose deterministic, bounded retry candidates from persisted state."""
    return [
        paper_id
        for paper_id, result in sorted(audit.items())
        if result.get("retryable") and paper_id not in (excluded or set())
    ][: max(0, limit)]


def build_report(
    audit: Mapping[int, Mapping[str, Any]],
    *,
    target: int,
    rounds: int,
    attempts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    states = Counter(str(result.get("state") or "unknown") for result in audit.values())
    reasons = Counter(
        reason
        for result in audit.values()
        for reason in result.get("reason_codes", [])
    )
    complete_ids = sorted(
        paper_id
        for paper_id, result in audit.items()
        if result.get("complete") or result.get("state") == "complete"
    )
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "target_complete": target,
        "complete_count": len(complete_ids),
        "target_reached": len(complete_ids) >= target,
        "total_papers": len(audit),
        "rounds": rounds,
        "states": dict(sorted(states.items())),
        "failure_reasons": dict(sorted(reasons.items())),
        "complete_paper_ids": complete_ids,
        "attempts": list(attempts),
    }


def write_reports(report: Mapping[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "literature-demo-stabilization.json"
    markdown_path = output_dir / "literature-demo-stabilization.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Literature demo stabilization report",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Target complete | {report['target_complete']} |",
        f"| Complete papers | {report['complete_count']} |",
        f"| Total papers | {report['total_papers']} |",
        f"| Target reached | {str(report['target_reached']).lower()} |",
        f"| Processing rounds | {report['rounds']} |",
        "",
        "## States",
        "",
        "| State | Count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {state} | {count} |" for state, count in report["states"].items())
    lines.extend(["", "## Failure reasons", "", "| Reason | Count |", "| --- | ---: |"]) 
    if report["failure_reasons"]:
        lines.extend(
            f"| {reason} | {count} |"
            for reason, count in report["failure_reasons"].items()
        )
    else:
        lines.append("| none | 0 |")
    lines.extend([
        "",
        "## Complete paper IDs",
        "",
        ", ".join(str(paper_id) for paper_id in report["complete_paper_ids"]) or "None",
        "",
    ])
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path


def _retry(proxy: ConsoleProgress, paper_id: int, stage: str) -> dict[str, Any]:
    from search.api import _retry_extract_task, _retry_parse_task

    result: dict[str, Any] = {"paper_id": paper_id, "action": "retry", "stage": stage}
    try:
        if stage != "extract":
            result["parse"] = _retry_parse_task(proxy, paper_id)
        result["extract"] = _retry_extract_task(proxy, paper_id)
        result["ok"] = True
    except Exception as exc:
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _collect_process(
    proxy: ConsoleProgress,
    topic: str,
    source: str,
    batch_size: int,
) -> dict[str, Any]:
    from search.api import _collect_task, _extract_task, _parse_task

    attempt: dict[str, Any] = {"action": "collect", "topic": topic, "source": source}
    try:
        collected = _collect_task(proxy, topic, batch_size, 1, source=source)
        paper_ids = collected.get("paper_ids", [])
        attempt["collection"] = collected
        attempt["parse"] = _parse_task(
            proxy, "all", max(batch_size, len(paper_ids)), False, paper_ids=paper_ids
        )
        attempt["extract"] = _extract_task(proxy, paper_ids=paper_ids)
        attempt["ok"] = True
    except Exception as exc:
        attempt["ok"] = False
        attempt["error"] = f"{type(exc).__name__}: {exc}"
    return attempt


def stabilize(
    *,
    target: int,
    topics: tuple[str, ...],
    sources: tuple[str, ...],
    batch_size: int,
    max_rounds: int,
    retry_limit: int,
) -> dict[str, Any]:
    proxy = ConsoleProgress()
    attempts: list[dict[str, Any]] = []
    completed_rounds = 0
    attempted_retries: set[int] = set()
    audit = audit_corpus()
    for round_index in range(max_rounds):
        if sum(1 for result in audit.values() if result.get("state") == "complete") >= target:
            break
        completed_rounds += 1

        for paper_id in choose_retry_ids(audit, retry_limit, attempted_retries):
            attempts.append(_retry(proxy, paper_id, str(audit[paper_id].get("stage"))))
            attempted_retries.add(paper_id)

        audit = audit_corpus()
        if sum(1 for result in audit.values() if result.get("state") == "complete") >= target:
            break

        topic = topics[round_index % len(topics)]
        source = sources[round_index % len(sources)]
        attempts.append(_collect_process(proxy, topic, source, batch_size))
        audit = audit_corpus()

    return build_report(
        audit, target=target, rounds=completed_rounds, attempts=attempts
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect, process, retry and audit an open-literature demo corpus."
    )
    parser.add_argument("--target", type=int, default=30, help="required complete-paper count")
    parser.add_argument("--topics", default=",".join(DEFAULT_TOPICS))
    parser.add_argument("--sources", default=",".join(DEFAULT_SOURCES))
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-rounds", type=int, default=8)
    parser.add_argument("--retry-limit", type=int, default=10)
    parser.add_argument(
        "--report-dir", type=Path, default=PROJECT_ROOT.parent / "docs" / "reports"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    topics = tuple(item.strip() for item in args.topics.split(",") if item.strip())
    sources = tuple(item.strip() for item in args.sources.split(",") if item.strip())
    if not topics or not sources:
        raise SystemExit("At least one topic and one source are required.")
    report = stabilize(
        target=max(1, args.target), topics=topics, sources=sources,
        batch_size=max(1, args.batch_size), max_rounds=max(1, args.max_rounds),
        retry_limit=max(0, args.retry_limit),
    )
    json_path, markdown_path = write_reports(report, args.report_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    return 0 if report["target_reached"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
