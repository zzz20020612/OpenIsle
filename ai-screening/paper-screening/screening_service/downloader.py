from __future__ import annotations

import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx


class ManuscriptDownloader:
    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    def download(self, url: str, filename: str) -> Path:
        suffix = Path(filename).suffix.lower() or Path(urlparse(url).path).suffix.lower()
        if suffix not in {".pdf", ".docx", ".txt", ".tex"}:
            suffix = ".bin"
        with httpx.stream("GET", url, timeout=self.timeout, follow_redirects=True) as response:
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as target:
                for chunk in response.iter_bytes():
                    target.write(chunk)
                return Path(target.name)

    @staticmethod
    def cleanup(path: Path) -> None:
        path.unlink(missing_ok=True)
