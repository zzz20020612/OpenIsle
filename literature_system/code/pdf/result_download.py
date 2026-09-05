"""MinerU CDN download with an opt-in, certificate-verified DNS fallback."""
import ipaddress
from urllib.parse import urlsplit, urlunsplit

import requests
import urllib3


def download_result(url, fallback_proxy=""):
    try:
        with requests.get(url, timeout=120) as response:
            response.raise_for_status()
            return response.content
    except requests.exceptions.ConnectionError:
        if not fallback_proxy:
            raise

    target = urlsplit(url)
    # Never send arbitrary hosts or API credentials through the fallback.
    if (target.scheme != "https" or target.hostname != "cdn-mineru.openxlab.org.cn"
            or target.port not in (None, 443) or target.username or target.password):
        raise requests.RequestException("MinerU fallback only supports its HTTPS CDN")
    with requests.get(
        "https://dns.alidns.com/resolve",
        params={"name": target.hostname, "type": "A"}, timeout=15,
    ) as response:
        response.raise_for_status()
        answers = response.json().get("Answer", [])
    addresses = []
    for answer in answers:
        if answer.get("type") != 1:
            continue
        try:
            address = ipaddress.ip_address(answer.get("data", ""))
        except ValueError:
            continue
        if address.version == 4 and address.is_global:
            addresses.append(str(address))
    for address in addresses[:3]:
        # CONNECT to the resolved address, but validate TLS against the real host.
        manager = urllib3.ProxyManager(
            fallback_proxy, server_hostname=target.hostname,
            assert_hostname=target.hostname, cert_reqs="CERT_REQUIRED",
        )
        try:
            response = manager.request(
                "GET", urlunsplit(("https", address, target.path, target.query, "")),
                headers={"Host": target.hostname}, timeout=120,
                retries=False, redirect=False,
            )
            if response.status == 200:
                return response.data
        except urllib3.exceptions.HTTPError:
            pass
        finally:
            manager.clear()
    raise requests.RequestException("MinerU CDN download failed through verified fallback")
