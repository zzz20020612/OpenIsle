from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from scripts.check_logic import check_logic
from scripts.check_references import check_references
from scripts.check_sensitive import check_sensitive
from scripts.generate_report import (
    _determine_verdict,
    generate_report,
    normalize_dimension,
)
from scripts.parse_paper import parse_paper


class ModelClient(Protocol):
    def analyze(
        self,
        dimension_id: str,
        instruction: str,
        paper: dict[str, Any],
        prior_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


_AGENT_FILES = {
    "01": "dim-01-format.md",
    "05": "dim-05-ethics.md",
    "07": "dim-07-authorship.md",
    "08": "dim-08-language.md",
}

_DIMENSION_NAMES = {
    "01": "格式与结构",
    "02": "重复文本",
    "03": "图像完整性",
    "04": "科学逻辑",
    "05": "伦理法规",
    "06": "敏感内容",
    "07": "署名版权",
    "08": "语言引用",
    "09": "综合分流",
}

_VERDICT_STATUS = {
    "Publish": ("publish", "PASSED", "LOW"),
    "Minor Revision": ("minor_revision", "NEEDS_REVISION", "MEDIUM"),
    "Major Revision": ("major_revision", "NEEDS_REVISION", "HIGH"),
    "Conditional": ("conditional", "REJECTED_BY_POLICY", "HIGH"),
    "Reject": ("reject", "REJECTED_BY_POLICY", "HIGH"),
}


def _skipped(dimension_id: str, reason: str) -> dict[str, Any]:
    return {
        "dimension_id": dimension_id,
        "dimension_name": _DIMENSION_NAMES[dimension_id],
        "status": "skipped",
        "severity": "info",
        "findings": [{"item": "MVP 范围", "actual": reason}],
        "interaction_needed": False,
        "user_response": None,
    }


class ScreeningPipeline:
    def __init__(self, model_client: ModelClient) -> None:
        self.model_client = model_client
        self.root = Path(__file__).resolve().parent.parent

    def screen_file(
        self,
        *,
        paper_id: int,
        manuscript_path: Path,
        title: str,
        authors: list[str],
        subject_area: str,
        paper_type: str,
        declarations: dict[str, Any],
    ) -> dict[str, Any]:
        paper = parse_paper(str(manuscript_path))
        if not paper.get("metadata") or not paper.get("segments"):
            raise ValueError("Parsed manuscript contains no text segments")

        paper["metadata"].update(
            title=title or paper["metadata"].get("title", "Untitled"),
            authors=authors or paper["metadata"].get("authors", []),
            subject_area=subject_area,
            paper_type=paper_type,
        )
        paper["declarations"] = declarations

        results: list[dict[str, Any]] = []
        results.append(self._model_dimension("01", paper))
        results.append(_skipped("02", "文本查重未执行"))
        results.append(_skipped("03", "图片完整性检查未执行"))
        results.append(normalize_dimension(check_logic(paper)))
        results.append(self._model_dimension("05", paper))
        results.append(normalize_dimension(check_sensitive(paper)))
        results.append(self._model_dimension("07", paper))

        reference_result = normalize_dimension(check_references(paper))
        results.append(self._model_dimension("08", paper, reference_result))

        verdict_info = _determine_verdict(results)
        results.append(self._verdict_dimension(verdict_info))
        verdict, status, risk_level = _VERDICT_STATUS[verdict_info["archetype"]]
        report = generate_report(results, title, authors)

        return {
            "paperId": paper_id,
            "verdict": verdict,
            "status": status,
            "riskLevel": risk_level,
            "summary": verdict_info["reason"],
            "dimensions": results,
            "skippedDimensions": ["02", "03"],
            "reportMarkdown": report,
            "rawResult": verdict_info,
        }

    def _model_dimension(
        self,
        dimension_id: str,
        paper: dict[str, Any],
        prior_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        instruction_path = self.root / "agents" / _AGENT_FILES[dimension_id]
        instruction = instruction_path.read_text(encoding="utf-8")
        result = self.model_client.analyze(
            dimension_id,
            instruction,
            paper,
            prior_result,
        )
        normalized = normalize_dimension(result)
        normalized["dimension_id"] = dimension_id
        normalized["dimension_name"] = _DIMENSION_NAMES[dimension_id]
        return normalized

    @staticmethod
    def _verdict_dimension(verdict_info: dict[str, Any]) -> dict[str, Any]:
        archetype = verdict_info["archetype"]
        status = "passed" if archetype == "Publish" else (
            "warning" if archetype in {"Minor Revision", "Major Revision"} else "failed"
        )
        severity = {
            "Publish": "info",
            "Minor Revision": "minor",
            "Major Revision": "major",
            "Conditional": "critical",
            "Reject": "critical",
        }[archetype]
        return {
            "dimension_id": "09",
            "dimension_name": _DIMENSION_NAMES["09"],
            "status": status,
            "severity": severity,
            "findings": [],
            "interaction_needed": False,
            "user_response": None,
            "verdict": archetype,
            "verdict_reason": verdict_info["reason"],
            "triggered_dimensions": verdict_info["triggered"],
        }
