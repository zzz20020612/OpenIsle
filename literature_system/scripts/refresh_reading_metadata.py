"""Reconcile saved reading metadata without downloading PDFs or invoking LLMs.

Run with --apply to persist; the default is a dry run. Section IDs are preserved.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from pdf.scheduler import get_conn
from pdf.reading import abstract_from_sections, reading_sections
from pdf.ref_parser import extract_doi_from_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    conn = get_conn()
    counts = {'abstracts': 0, 'sections': 0, 'references': 0}
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, abstract FROM papers')
        papers = cur.fetchall()
        for paper in papers:
            paper_id, abstract = paper[0], paper[1]
            cur.execute('SELECT id, heading, content, section_type FROM paper_sections WHERE paper_id=? ORDER BY order_idx', (paper_id,))
            sections = [dict(zip(['id','heading','content','section_type'], row)) for row in cur.fetchall()]
            recovered = abstract_from_sections(sections) if not abstract else ''
            if recovered:
                counts['abstracts'] += 1
                if args.apply:
                    cur.execute('UPDATE papers SET abstract=? WHERE id=?', (recovered, paper_id))
            for old, new in zip(sections, reading_sections(sections)):
                if old['section_type'] != new['section_type']:
                    counts['sections'] += 1
                    if args.apply:
                        cur.execute('UPDATE paper_sections SET section_type=? WHERE id=?', (new['section_type'], new['id']))
        cur.execute('SELECT id, raw_reference, cited_doi FROM citations_v2 WHERE match_method = ?', ('doi_lookup',))
        for ref_id, raw, doi in cur.fetchall():
            repaired = extract_doi_from_text(raw or '')
            if repaired and doi and repaired.startswith(doi) and repaired != doi:
                counts['references'] += 1
                if args.apply:
                    cur.execute('UPDATE citations_v2 SET cited_doi=?, match_confidence=? WHERE id=?', (repaired, 'low', ref_id))
        if args.apply:
            conn.commit()
        print(json.dumps({'applied': args.apply, **counts}))
    finally:
        conn.close()


if __name__ == '__main__':
    main()
