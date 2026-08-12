from pathlib import Path

from scripts import parse_paper


def test_pdf_parser_uses_ocr_when_text_layer_is_empty(monkeypatch, tmp_path: Path):
    manuscript = tmp_path / "scan.pdf"
    manuscript.write_bytes(b"%PDF test")
    text_parse = {
        "metadata": {"format": "pdf", "page_count": 1, "title": ""},
        "segments": [],
        "images": [],
        "tables": [],
        "declarations": {},
    }
    ocr_parse = {**text_parse, "segments": [{"type": "body", "text": "OCR text"}]}

    monkeypatch.setattr(parse_paper, "_parse_pdf_pdfplumber", lambda path: text_parse)
    monkeypatch.setattr(parse_paper, "_parse_pdf_ocr", lambda path, parsed: ocr_parse)

    assert parse_paper._parse_pdf(manuscript)["segments"] == ocr_parse["segments"]
