from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default_factory=lambda: os.getenv("AI_SCREENING_API_KEY", ""))
    base_url: str = field(
        default_factory=lambda: os.getenv("AI_SCREENING_BASE_URL", "https://api.openai.com/v1")
    )
    model: str = field(default_factory=lambda: os.getenv("AI_SCREENING_MODEL", "gpt-4o-mini"))
    service_token: str = field(
        default_factory=lambda: os.getenv("AI_SCREENING_SERVICE_TOKEN", "")
    )
    request_timeout: float = field(
        default_factory=lambda: float(os.getenv("AI_SCREENING_REQUEST_TIMEOUT", "90"))
    )
    internal_base_url: str = field(
        default_factory=lambda: os.getenv("AI_SCREENING_INTERNAL_BASE_URL", "")
    )
