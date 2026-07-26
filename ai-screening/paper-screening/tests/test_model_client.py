import json

import httpx
import pytest

from screening_service.config import Settings
from screening_service.model_client import OpenAICompatibleModelClient


def _paper():
    return {
        "metadata": {"title": "Paper"},
        "segments": [{"type": "abstract", "text": "A concise abstract"}],
        "declarations": {},
    }


def test_model_client_requests_json_and_returns_dimension():
    dimension = {
        "dimension_id": "01",
        "dimension_name": "格式与结构",
        "status": "passed",
        "severity": "info",
        "findings": [],
        "interaction_needed": False,
    }

    def handler(request: httpx.Request):
        body = json.loads(request.content)
        assert body["response_format"] == {"type": "json_object"}
        assert request.headers["Authorization"] == "Bearer key"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(dimension)}}]},
        )

    client = OpenAICompatibleModelClient(
        Settings(api_key="key", base_url="https://model.example/v1", model="model"),
        transport=httpx.MockTransport(handler),
    )

    assert client.analyze("01", "instructions", _paper()) == dimension


def test_model_client_rejects_invalid_json():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"choices": [{"message": {"content": "not json"}}]}
        )
    )
    client = OpenAICompatibleModelClient(
        Settings(api_key="key"), transport=transport
    )

    with pytest.raises(ValueError, match="valid dimension JSON"):
        client.analyze("01", "instructions", _paper())
