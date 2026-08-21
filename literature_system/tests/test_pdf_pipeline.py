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


class PdfStructureHelpersTest(unittest.TestCase):
    def test_numbered_headings_are_classified_semantically(self):
        self.assertEqual("results", pipeline.classify_section("3. Results"))
        self.assertEqual("methods", pipeline.classify_section("2.1 Study Area"))

    def test_body_sentences_are_not_treated_as_headings(self):
        line = {
            "text": "finding fundamentally challenges the conventional assumption",
            "size": 12,
            "bold": False,
        }
        self.assertFalse(pipeline._looks_like_section_heading(line, 12))

    def test_layout_heading_is_retained(self):
        line = {"text": "4. Discussion", "size": 15, "bold": True}
        self.assertTrue(pipeline._looks_like_section_heading(line, 12))

    def test_visual_lines_are_dehyphenated(self):
        self.assertEqual(
            "high-resolution manuscript",
            pipeline._join_pdf_lines(["high-resolu-", "tion manuscript"]),
        )

    def test_coordinate_gaps_restore_spaces_between_pdf_spans(self):
        spans = [
            {"text": "Achieving", "bbox": (60, 70, 105, 84), "size": 11},
            {"text": "water", "bbox": (110, 70, 137, 84), "size": 11},
            {"text": "security", "bbox": (142, 70, 180, 84), "size": 11},
        ]
        self.assertEqual("Achieving water security", pipeline._join_pdf_spans(spans))

    def test_touching_pdf_spans_do_not_split_a_word(self):
        spans = [
            {"text": "environ", "bbox": (60, 70, 97, 84), "size": 11},
            {"text": "mental", "bbox": (97.2, 70, 130, 84), "size": 11},
        ]
        self.assertEqual("environmental", pipeline._join_pdf_spans(spans))

    def test_standalone_parse_keeps_manuscript_out_of_literature_database(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_pdf = Path(directory) / "missing.pdf"
            with self.assertRaises(FileNotFoundError):
                pipeline.parse_pdf_document(missing_pdf, ["pymupdf"])


if __name__ == "__main__":
    unittest.main()
