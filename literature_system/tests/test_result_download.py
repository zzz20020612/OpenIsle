import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from pdf.result_download import download_result

URL = "https://cdn-mineru.openxlab.org.cn/pdf/test.zip"


def test_normal_download():
    with patch("pdf.result_download.requests.get") as get:
        get.return_value.__enter__.return_value.content = b"zip"
        assert download_result(URL) == b"zip"
        assert get.call_count == 1


def test_fallback_is_opt_in():
    with patch("pdf.result_download.requests.get", side_effect=requests.exceptions.SSLError):
        with pytest.raises(requests.exceptions.SSLError):
            download_result(URL)


def test_fallback_preserves_certificate_hostname_and_filters_private_ips():
    dns = MagicMock()
    dns.__enter__.return_value.json.return_value = {"Answer": [
        {"type": 1, "data": "127.0.0.1"},
        {"type": 1, "data": "198.18.0.13"},
        {"type": 1, "data": "112.15.7.179"},
    ]}
    with patch("pdf.result_download.requests.get", side_effect=[requests.exceptions.SSLError(), dns]), patch("pdf.result_download.urllib3.ProxyManager") as proxy:
        proxy.return_value.request.return_value.status = 200
        proxy.return_value.request.return_value.data = b"zip"
        assert download_result(URL, "http://proxy:7897") == b"zip"
        assert proxy.call_args.kwargs["assert_hostname"] == "cdn-mineru.openxlab.org.cn"
        assert proxy.call_args.kwargs["cert_reqs"] == "CERT_REQUIRED"
        assert proxy.return_value.request.call_args.args[1] == "https://112.15.7.179/pdf/test.zip"
        proxy.return_value.clear.assert_called_once()


def test_other_hosts_never_use_fallback():
    with patch("pdf.result_download.requests.get", side_effect=requests.exceptions.SSLError), patch("pdf.result_download.urllib3.ProxyManager") as proxy:
        with pytest.raises(requests.RequestException):
            download_result("https://example.com/a", "http://proxy:7897")
        proxy.assert_not_called()


def test_mineru_uses_flat_content_list_when_v2_is_also_present(tmp_path, monkeypatch):
    import json
    import config
    from pdf.pipeline import MineruAPIClient

    monkeypatch.setattr(config, "MINERU_API_KEY", "test-only")
    monkeypatch.setattr(config, "PDF_DOWNLOAD_DIR", str(tmp_path))
    (tmp_path / "full.md").write_text("# Introduction\nA test paper.", encoding="utf-8")
    (tmp_path / "paper_content_list_v2.json").write_text("[[{}]]", encoding="utf-8")
    (tmp_path / "paper_content_list.json").write_text(json.dumps([
        {"type": "text", "text": "Introduction", "text_level": 1, "page_idx": 0},
        {"type": "text", "text": "A test paper.", "page_idx": 0},
    ]), encoding="utf-8")
    result = MineruAPIClient()._convert_result(tmp_path, tmp_path / "paper.pdf")
    assert result.page_count == 1
    assert len(result.sections) == 1
