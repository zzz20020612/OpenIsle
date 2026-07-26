from pathlib import Path

from fastapi.testclient import TestClient

from screening_service.api import create_app
from screening_service.config import Settings


class FakeDownloader:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.urls: list[str] = []
        self.filenames: list[str] = []

    def download(self, url: str, filename: str):
        self.urls.append(url)
        self.filenames.append(filename)
        return self.path


class FakePipeline:
    def __init__(self) -> None:
        self.calls = []

    def screen_file(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "paperId": kwargs["paper_id"],
            "verdict": "publish",
            "status": "PASSED",
            "riskLevel": "LOW",
            "summary": "文本初筛通过",
            "dimensions": [],
            "skippedDimensions": ["02", "03"],
            "reportMarkdown": "report",
            "rawResult": {},
        }


def test_screening_endpoint_requires_service_token(tmp_path: Path):
    manuscript = tmp_path / "paper.txt"
    manuscript.write_text("paper", encoding="utf-8")
    app = create_app(
        Settings(service_token="secret"),
        pipeline=FakePipeline(),
        downloader=FakeDownloader(manuscript),
    )

    response = TestClient(app).post("/v1/screenings", json={})

    assert response.status_code == 401


def test_screening_endpoint_downloads_and_screens_manuscript(tmp_path: Path):
    manuscript = tmp_path / "paper.txt"
    manuscript.write_text("paper", encoding="utf-8")
    pipeline = FakePipeline()
    downloader = FakeDownloader(manuscript)
    app = create_app(
        Settings(service_token="secret"),
        pipeline=pipeline,
        downloader=downloader,
    )

    response = TestClient(app).post(
        "/v1/screenings",
        headers={"Authorization": "Bearer secret"},
        json={
            "paperId": 12,
            "manuscriptUrl": "http://springboot/file/token",
            "manuscriptFileName": "paper.txt",
            "title": "Paper",
            "authors": ["Author"],
            "subjectArea": "Biology",
            "paperType": "Research Article",
            "declarations": {"ethicsStatement": "Approved"},
        },
    )

    assert response.status_code == 200
    assert response.json()["paperId"] == 12
    assert downloader.urls == ["http://springboot/file/token"]
    assert downloader.filenames == ["paper.txt"]
    assert pipeline.calls[0]["manuscript_path"] == manuscript
