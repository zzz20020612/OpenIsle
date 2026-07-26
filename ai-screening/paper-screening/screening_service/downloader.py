from __future__ import annotations

import tempfile
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import httpx


class ManuscriptDownloader:
    def __init__(self, timeout: float = 30.0, internal_base_url: str = "") -> None:
        self.timeout = timeout
        self.internal_base_url = internal_base_url.rstrip("/")

    def rewrite_url(self, url: str) -> str:
        if not self.internal_base_url:
            return url
        original = urlparse(url)
        replacement = urlparse(self.internal_base_url)
        if original.hostname not in {"localhost", "127.0.0.1"}:
            return url
        return urlunparse(
            original._replace(
                scheme=replacement.scheme,
                netloc=replacement.netloc,
            )
        )

    def download(self, url: str, filename: str) -> Path:
        url = self.rewrite_url(url)
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
