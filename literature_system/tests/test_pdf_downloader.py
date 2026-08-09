from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from pdf import downloader


class PdfDownloaderFallbackTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
