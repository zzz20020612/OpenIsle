from __future__ import annotations

import json
from typing import Any

import httpx

from scripts.generate_report import parse_dimension_json

from .config import Settings


class OpenAICompatibleModelClient:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.client = httpx.Client(
            base_url=settings.base_url.rstrip("/") + "/",
            timeout=settings.request_timeout,
            transport=transport,
        )

    def analyze(
        self,
        dimension_id: str,
        instruction: str,
        paper: dict[str, Any],
        prior_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.settings.api_key:
            raise ValueError("AI_SCREENING_API_KEY is required")

        paper_payload = self._compact_paper(paper)
        user_payload = {"paper": paper_payload, "ruleResult": prior_result}
        response = self.client.post(
            "chat/completions",
            headers={"Authorization": f"Bearer {self.settings.api_key}"},
            json={
                "model": self.settings.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            f"你是论文初筛维度 {dimension_id} 分析器。严格执行以下规则。"
                            "只输出规则定义的单个 JSON 对象，不输出推理过程或 Markdown。\n\n"
                            + instruction
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False),
                    },
                ],
            },
        )
        response.raise_for_status()
        try:
            raw = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError("Model response did not contain message content") from exc
        result = parse_dimension_json(raw)
        if result is None:
            raise ValueError("Model did not return valid dimension JSON")
        return result

    @staticmethod
    def _compact_paper(paper: dict[str, Any]) -> dict[str, Any]:
        remaining = 60_000
        segments = []
        for segment in paper.get("segments", []):
            if remaining <= 0:
                break
            text = str(segment.get("text", ""))[:remaining]
            remaining -= len(text)
            segments.append({**segment, "text": text})
        return {
            "metadata": paper.get("metadata", {}),
            "segments": segments,
            "declarations": paper.get("declarations", {}),
            "tables": paper.get("tables", []),
        }
