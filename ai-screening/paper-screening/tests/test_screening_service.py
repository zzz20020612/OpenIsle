from __future__ import annotations

from pathlib import Path

import pytest

from screening_service.pipeline import ScreeningPipeline


class FakeModelClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def analyze(self, dimension_id, instruction, paper, prior_result=None):
        self.calls.append(dimension_id)
        return {
            "dimension_id": dimension_id,
            "dimension_name": {
                "01": "格式与结构",
                "05": "伦理法规",
                "07": "署名版权",
                "08": "语言引用",
            }[dimension_id],
            "status": "passed",
            "severity": "info",
            "findings": [],
            "interaction_needed": False,
        }


def test_pipeline_runs_text_dimensions_in_skill_order(tmp_path: Path):
    manuscript = tmp_path / "paper.txt"
    manuscript.write_text(
        "A useful study\n\nAbstract\nObjective method result conclusion.\n\n"
        "Methods\nWe used a reproducible method.\n\n"
        "Results\nThe result was consistent.\n\n"
        "Conclusion\nThe conclusion follows.\n\nReferences\n[1] Example reference.",
        encoding="utf-8",
    )
    model = FakeModelClient()
    pipeline = ScreeningPipeline(model_client=model)

    response = pipeline.screen_file(
        paper_id=42,
        manuscript_path=manuscript,
        title="A useful study",
        authors=["Ada Lovelace"],
        subject_area="Computer Science",
        paper_type="Research Article",
        declarations={},
    )

    assert model.calls == ["01", "05", "07", "08"]
    assert [item["dimension_id"] for item in response["dimensions"]] == [
        "01", "02", "03", "04", "05", "06", "07", "08", "09"
    ]
    assert response["skippedDimensions"] == ["02", "03"]
    assert response["dimensions"][1]["status"] == "skipped"
    assert response["dimensions"][2]["status"] == "skipped"
    assert response["paperId"] == 42
    assert response["status"] == "PASSED"
    assert response["verdict"] == "publish"
    assert "分流建议" in response["reportMarkdown"]


def test_pipeline_maps_revision_verdict_to_needs_revision(tmp_path: Path):
    manuscript = tmp_path / "paper.txt"
    manuscript.write_text("Title\n\nAbstract\nShort abstract.", encoding="utf-8")

    class RevisionModel(FakeModelClient):
        def analyze(self, dimension_id, instruction, paper, prior_result=None):
            result = super().analyze(dimension_id, instruction, paper, prior_result)
            if dimension_id == "05":
                result.update(status="warning", severity="major")
                result["findings"] = [{"item": "伦理审批", "actual": "缺少声明"}]
            return result

    response = ScreeningPipeline(model_client=RevisionModel()).screen_file(
        paper_id=7,
        manuscript_path=manuscript,
        title="Title",
        authors=[],
        subject_area="Medicine",
        paper_type="Research Article",
        declarations={},
    )

    assert response["verdict"] == "minor_revision"
    assert response["status"] == "NEEDS_REVISION"
    assert response["riskLevel"] == "MEDIUM"


def test_pipeline_rejects_empty_parse_result(tmp_path: Path):
    manuscript = tmp_path / "empty.txt"
    manuscript.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="no text segments"):
        ScreeningPipeline(model_client=FakeModelClient()).screen_file(
            paper_id=9,
            manuscript_path=manuscript,
            title="Empty",
            authors=[],
            subject_area="Other",
            paper_type="Other",
            declarations={},
        )
