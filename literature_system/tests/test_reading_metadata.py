import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from pdf.reading import abstract_from_sections, reading_sections


def test_embedded_abstract_excludes_authors_and_keywords():
    text = 'A study of water monitoring and sensor accuracy. ' * 3
    sections = [{'content': 'Author\nInstitution\nAbstract: ' + text + '\nKeywords: water'}]
    assert abstract_from_sections(sections) == text.strip()


def test_does_not_invent_abstract_from_introduction():
    assert abstract_from_sections([{'content': 'Introduction\n' + 'Water study. ' * 30}]) == ''


def test_preserves_identity_and_numbered_depth():
    source = {'id': 42, 'heading': '2.1 Related Work', 'section_type': 'results'}
    result = reading_sections([source])[0]
    assert result['heading_level'] == 2
    assert result['section_type'] == 'background'
    assert result['id'] == 42
    assert source['section_type'] == 'results'


def test_doi_layout_repair():
    from pdf.ref_parser import extract_doi_from_text
    assert extract_doi_from_text('doi: https: //doi. org/10.1016/j. jpse.2022.01.003.') == '10.1016/j.jpse.2022.01.003'
    assert extract_doi_from_text('doi 10.1186/s13638 - 018 - 1316 - x.') == '10.1186/s13638-018-1316-x'
    assert extract_doi_from_text('10.1175/jcli-d-14-00750.1. This is another sentence') == '10.1175/jcli-d-14-00750.1'
