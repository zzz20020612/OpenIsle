from abc import ABC, abstractmethod
import time
import requests


class SourceAdapter(ABC):
    name: str

    def request_with_retry(
        self,
        url,
        params=None,
        headers=None,
        method="GET",
        json=None,
        max_retries=5,
        backoff=2,
        timeout=30,
    ):
        """带重试的 HTTP 请求，支持 GET/POST。"""
        method = method.upper()
        for attempt in range(1, max_retries + 1):
            try:
                if method == "POST":
                    resp = requests.post(
                        url, params=params, headers=headers, json=json, timeout=timeout
                    )
                else:
                    resp = requests.get(
                        url, params=params, headers=headers, timeout=timeout
                    )
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(backoff * attempt)
                    continue
                resp.raise_for_status()
                return resp
            except requests.RequestException:
                time.sleep(backoff * attempt)
        raise RuntimeError("请求失败，已超过最大重试次数")

    @abstractmethod
    def fetch(self, keyword: str, page: int, page_size: int):
        """返回标准化后的结果列表，字段尽量与 Crossref 一致"""
        raise NotImplementedError
