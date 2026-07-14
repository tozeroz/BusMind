from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class DeepSeekError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DeepSeekConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = 20.0
    max_tokens: int = 700
    temperature: float = 0.2


class DeepSeekClient:
    """Minimal async client for DeepSeek's OpenAI-compatible Chat API."""

    def __init__(self, config: DeepSeekConfig) -> None:
        self.config = config

    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
    ) -> str:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "thinking": {"type": "disabled"},
        }
        if response_format is not None:
            payload["response_format"] = response_format
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                trust_env=False,
            ) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise DeepSeekError("DeepSeek 请求超时") from exc
        except httpx.HTTPError as exc:
            raise DeepSeekError("DeepSeek 网络请求失败") from exc
        except (ImportError, OSError) as exc:
            raise DeepSeekError("DeepSeek HTTP 客户端初始化失败") from exc

        if response.status_code >= 400:
            safe_message = _extract_error_message(response)
            raise DeepSeekError(
                f"DeepSeek API 返回 {response.status_code}: {safe_message}"
            )
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise DeepSeekError("DeepSeek 响应结构不完整") from exc
        if not isinstance(content, str) or not content.strip():
            raise DeepSeekError("DeepSeek 未返回有效回答")
        return content.strip()


def _extract_error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
        message = data.get("error", {}).get("message")
        if isinstance(message, str):
            return message[:200]
    except ValueError:
        pass
    return "请求失败"
