from __future__ import annotations

import sys
import io
import tarfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from pdf import downloader


class PdfDownloaderFallbackTest(unittest.TestCase):
    def test_downloads_pdf_from_official_pmc_oa_package(self):
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w:gz") as bundle:
            content = b"%PDF-1.7\nopen article"
            info = tarfile.TarInfo("PMC123/article.pdf")
            info.size = len(content)
            bundle.addfile(info, io.BytesIO(content))
        response = Mock(status_code=200, content=archive.getvalue())
        response.headers = {"content-type": "application/gzip"}

        with (
            patch.object(downloader.requests, "get", return_value=response),
            patch.object(downloader, "PDF_DIR", self._temporary_directory()),
        ):
            success, path, error = downloader.download_pdf(
                "https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/demo.tar.gz",
                "oa:PMC123",
            )

        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(b"%PDF", Path(path).read_bytes()[:4])

    def _temporary_directory(self):
        import tempfile
        return Path(tempfile.mkdtemp())

    def test_tries_later_provider_when_first_candidate_is_not_a_pdf(self):
        attempts = []

        def fake_download(url, doi, timeout, max_retries):
            attempts.append(url)
            if url == "https://publisher.example/landing":
                return False, None, "not a PDF"
            return True, "/tmp/paper.pdf", None

        strategy = {
            "crossref_text_mining": 0,
            "crossref_pdf": 0,
            "oa_url": 1,
            "doi_redirect": 2,
            "unpaywall": 3,
        }
        with (
            patch.object(downloader.config, "PDF_DOWNLOAD_STRATEGY", strategy),
            patch.object(downloader, "download_pdf", side_effect=fake_download),
            patch.object(downloader, "_get_doi_redirect_url", return_value="https://publisher.example/landing"),
            patch.object(downloader, "_get_unpaywall_url", return_value="https://repository.example/paper.pdf"),
        ):
            result = downloader.download_pdf_with_fallback(
                "10.1234/example",
                oa_url="https://publisher.example/landing",
            )

        self.assertEqual((True, "/tmp/paper.pdf", None), result)
        self.assertEqual(
            ["https://publisher.example/landing", "https://repository.example/paper.pdf"],
            attempts,
        )

    def test_plos_landing_page_is_converted_to_printable_pdf(self):
        response = Mock()
        response.url = (
            "https://journals.plos.org/plosmedicine/article"
            "?id=10.1371/journal.pmed.1001747"
        )
        response.headers = {"content-type": "text/html;charset=UTF-8"}

        with patch.object(downloader.requests, "get", return_value=response):
            result = downloader._get_doi_redirect_url(
                "10.1371/journal.pmed.1001747",
                timeout=30,
                headers={},
            )

        self.assertEqual(
            "https://journals.plos.org/plosmedicine/article/file"
            "?id=10.1371/journal.pmed.1001747&type=printable",
            result,
        )


if __name__ == "__main__":
    unittest.main()
