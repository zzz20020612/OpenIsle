from __future__ import annotations

import sys
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parents[1] / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from sources.pmc import _parse_oa_package_url


def test_parses_https_package_url_for_open_pmc_record():
    xml = '''<OA><records><record id="PMC123"><link format="tgz"
      href="ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/a/b/PMC123.tar.gz" />
      </record></records></OA>'''

    assert _parse_oa_package_url(xml) == (
        "https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/a/b/PMC123.tar.gz"
    )


def test_non_open_pmc_record_has_no_package_url():
    xml = '<OA><error code="idIsNotOpenAccess">not open</error></OA>'

    assert _parse_oa_package_url(xml) is None
