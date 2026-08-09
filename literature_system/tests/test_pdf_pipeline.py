from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


CODE_ROOT = Path(__file__).resolve().parents[1] / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from pdf import pipeline


class PdfPathIsolationTest(unittest.TestCase):
    def test_paper_id_never_matches_a_different_doi_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf_dir = Path(directory)
            wrong_pdf = pdf_dir / "10.1371_journal.pmed.0020124.pdf"
            wrong_pdf.write_bytes(b"%PDF-1.4 wrong paper")

            with patch.object(pipeline.config, "PDF_DOWNLOAD_DIR", str(pdf_dir)):
                result = pipeline.get_pdf_path(2, "10.7717/peerj.4375")

            self.assertIsNone(result)

    def test_exact_paper_id_filename_is_allowed_without_doi_file(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf_dir = Path(directory)
            expected = pdf_dir / "2.pdf"
            expected.write_bytes(b"%PDF-1.4 exact paper")

            with patch.object(pipeline.config, "PDF_DOWNLOAD_DIR", str(pdf_dir)):
                result = pipeline.get_pdf_path(2, None)

            self.assertEqual(expected, result)


if __name__ == "__main__":
    unittest.main()
