from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .config import Settings
from .downloader import ManuscriptDownloader
from .model_client import OpenAICompatibleModelClient
from .pipeline import ScreeningPipeline


class ScreeningRequest(BaseModel):
    paper_id: int = Field(alias="paperId")
    manuscript_url: str = Field(alias="manuscriptUrl")
    manuscript_file_name: str = Field(alias="manuscriptFileName")
    title: str
    authors: list[str] = Field(default_factory=list)
    subject_area: str = Field(alias="subjectArea")
    paper_type: str = Field(alias="paperType")
    declarations: dict[str, Any] = Field(default_factory=dict)


def create_app(
    settings: Settings | None = None,
    *,
    pipeline: ScreeningPipeline | None = None,
    downloader: ManuscriptDownloader | None = None,
) -> FastAPI:
    settings = settings or Settings()
    pipeline = pipeline or ScreeningPipeline(OpenAICompatibleModelClient(settings))
    downloader = downloader or ManuscriptDownloader(internal_base_url=settings.internal_base_url)
    app = FastAPI(title="OpenIsle AI Screening", version="1.0.0")

    def require_token(authorization: str | None = Header(default=None)) -> None:
        expected = settings.service_token
        if not expected or authorization != f"Bearer {expected}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/screenings", dependencies=[Depends(require_token)])
    def screen(request: ScreeningRequest) -> dict[str, Any]:
        manuscript_path: Path | None = None
        try:
            manuscript_path = downloader.download(
                request.manuscript_url,
                request.manuscript_file_name,
            )
            return pipeline.screen_file(
                paper_id=request.paper_id,
                manuscript_path=manuscript_path,
                title=request.title,
                authors=request.authors,
                subject_area=request.subject_area,
                paper_type=request.paper_type,
                declarations=request.declarations,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        finally:
            if manuscript_path is not None and hasattr(downloader, "cleanup"):
                downloader.cleanup(manuscript_path)

    return app


app = create_app()
