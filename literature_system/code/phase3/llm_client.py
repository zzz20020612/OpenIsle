"""OpenAI 兼容 LLM 客户端。

支持 OpenAI / DeepSeek / 智谱 / 通义等任何兼容 OpenAI Chat Completions 接口的服务。
通过 config.LLM_BASE_URL 切换服务商。
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import config
from logger import get_logger

logger = get_logger("phase3.llm_client")


class LLMError(Exception):
    """LLM 调用异常。"""


class LLMClient:
    """OpenAI 兼容 LLM 客户端（基于 requests 库，无额外依赖）。

    使用 config 中的 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL 等配置。
    支持 OpenAI / DeepSeek / 智谱 / 通义等任何兼容 OpenAI Chat Completions 接口的服务。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or config.LLM_API_KEY
        self.base_url = (base_url or config.LLM_BASE_URL).rstrip("/")
        self.model = model or config.LLM_MODEL
        self.max_tokens = config.LLM_MAX_TOKENS
        self.temperature = config.LLM_TEMPERATURE
        self.timeout = config.LLM_REQUEST_TIMEOUT
        self.max_retries = config.LLM_MAX_RETRIES
        self.sleep_between = config.LLM_SLEEP_BETWEEN

        if not self.api_key:
            raise LLMError(
                "LLM_API_KEY 未配置。请在 .env 中设置 LLM_API_KEY 或 OPENAI_API_KEY。"
            )

        # 延迟导入 requests，避免未安装时影响其他模块
        try:
            import requests  # noqa: F401
            self._requests = requests
        except ImportError as e:
            raise LLMError(
                "requests 库未安装。请运行 pip install requests。"
            ) from e

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """调用 Chat Completions API，返回助手消息内容。

        Args:
            messages: OpenAI 消息列表 [{"role": "system", "content": "..."}, ...]
            temperature: 覆盖默认温度
            max_tokens: 覆盖默认最大 token 数
            response_format: 响应格式（如 {"type": "json_object"} 强制 JSON 输出）

        Returns:
            助手消息的 content 字符串

        Raises:
            LLMError: API 调用失败（重试耗尽后）
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._requests.post(
                    url, headers=headers, json=payload, timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                logger.debug(
                    "LLM 调用成功 model=%s tokens=%s",
                    self.model,
                    data.get("usage", {}).get("total_tokens", "?"),
                )
                if self.sleep_between > 0:
                    time.sleep(self.sleep_between)
                return content
            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM 调用失败 attempt=%d/%d error=%s", attempt, self.max_retries, e
                )
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # 指数退避

        raise LLMError(f"LLM 调用失败（重试 {self.max_retries} 次后）: {last_error}")

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """调用 LLM 并解析为 JSON 对象。

        使用 response_format={"type": "json_object"} 强制 JSON 输出。
        若 LLM 返回的 JSON 解析失败，尝试从 markdown code block 中提取。

        Returns:
            解析后的 JSON 字典

        Raises:
            LLMError: JSON 解析失败
        """
        content = self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return self._parse_json(content)

    @staticmethod
    def _parse_json(content: str) -> Dict[str, Any]:
        """Parse JSON with bounded repair for common model wrappers.

        Repair never invents values. It may remove surrounding prose or add
        closing brackets when the response ended at a valid JSON boundary.
        Semantically incomplete objects are rejected by the extractor and
        retried as independent components.
        """
        content = (content or "").strip()
        candidates = [content]
        if "```" in content:
            first = content.find("```") + 3
            first_line_end = content.find("\n", first)
            if first_line_end > first and content[first:first_line_end].strip().lower() == "json":
                first = first_line_end + 1
            end = content.find("```", first)
            if end > first:
                candidates.insert(0, content[first:end].strip())

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

            start = candidate.find("{")
            if start < 0:
                continue
            stack: List[str] = []
            in_string = False
            escaped = False
            for index, char in enumerate(candidate[start:], start=start):
                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        in_string = False
                    continue
                if char == '"':
                    in_string = True
                elif char in "{[":
                    stack.append(char)
                elif char in "}]":
                    if not stack or (char == "}" and stack[-1] != "{") or (char == "]" and stack[-1] != "["):
                        break
                    stack.pop()
                    if not stack:
                        try:
                            parsed = json.loads(candidate[start:index + 1])
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            break

            fragment = candidate[start:].rstrip()
            if stack and not in_string and fragment[-1:] not in {",", ":"}:
                repaired = fragment + "".join("}" if opener == "{" else "]" for opener in reversed(stack))
                try:
                    parsed = json.loads(repaired)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass
        raise LLMError(f"无法解析 LLM 返回的 JSON: {content[:200]}...")


class EmbeddingClient:
    """OpenAI 兼容 Embedding 客户端。

    使用 config 中的 EMBEDDING_API_KEY / EMBEDDING_BASE_URL / EMBEDDING_MODEL 等配置。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or config.EMBEDDING_API_KEY
        self.base_url = (base_url or config.EMBEDDING_BASE_URL).rstrip("/")
        self.model = model or config.EMBEDDING_MODEL
        self.batch_size = config.EMBEDDING_BATCH_SIZE
        self.timeout = config.LLM_REQUEST_TIMEOUT
        self.max_retries = config.LLM_MAX_RETRIES

        if not self.api_key:
            raise LLMError(
                "EMBEDDING_API_KEY 未配置。请在 .env 中设置 EMBEDDING_API_KEY 或 LLM_API_KEY。"
            )

        try:
            import requests  # noqa: F401
            self._requests = requests
        except ImportError as e:
            raise LLMError("requests 库未安装") from e

    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量。

        Args:
            texts: 待向量化的文本列表

        Returns:
            向量列表（每个向量是 float 列表，维度 = config.EMBEDDING_DIM）
        """
        all_embeddings: List[List[float]] = []
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            payload = {"model": self.model, "input": batch}

            last_error: Optional[Exception] = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    resp = self._requests.post(
                        url, headers=headers, json=payload, timeout=self.timeout
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    batch_embeddings = [item["embedding"] for item in data["data"]]
                    all_embeddings.extend(batch_embeddings)
                    logger.debug(
                        "Embedding 批次 %d-%d 成功 dim=%d",
                        i,
                        i + len(batch),
                        len(batch_embeddings[0]) if batch_embeddings else 0,
                    )
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(
                        "Embedding 批次 %d 失败 attempt=%d/%d error=%s",
                        i,
                        attempt,
                        self.max_retries,
                        e,
                    )
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
            else:
                raise LLMError(
                    f"Embedding 批次 {i}-{i+len(batch)} 失败: {last_error}"
                )

        return all_embeddings

    def embed_single(self, text: str) -> List[float]:
        """生成单个文本的向量。"""
        return self.embed([text])[0]
