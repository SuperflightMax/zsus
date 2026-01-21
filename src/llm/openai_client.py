"""OpenAI HTTP client using stdlib."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class OpenAIResponse:
    ok: bool
    content: Optional[str]
    status_code: Optional[int]
    error: Optional[str] = None


class OpenAIClient:
    """Minimal OpenAI chat completion client."""

    def __init__(self, config: Dict[str, Any]):
        llm_config = config.get("llm", {})
        self._api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL") or llm_config.get("api_url") or "https://api.openai.com/v1"
        self._api_url = f"{base_url.rstrip('/')}/chat/completions"
        self._model = os.getenv("OPENAI_MODEL") or llm_config.get("model", "gpt-4o-mini")
        self._temperature = llm_config.get("temperature", 0)
        self._max_tokens = llm_config.get("max_tokens", 300)
        self._timeout_s = llm_config.get("timeout_s", 20)
        retry_cfg = llm_config.get("retry", {})
        self._max_retries = retry_cfg.get("max_retries", 1)
        self._retry_backoff_s = retry_cfg.get("backoff_s", 1)

    def chat(self, messages: List[Dict[str, str]]) -> OpenAIResponse:
        if not self._api_key:
            return OpenAIResponse(ok=False, content=None, status_code=None, error="OPENAI_API_KEY missing")

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }

        attempt = 0
        while True:
            attempt += 1
            result = self._post_json(payload)
            if result.ok:
                return result

            if attempt <= self._max_retries and result.status_code in {429, 500, 502, 503, 504}:
                time.sleep(self._retry_backoff_s)
                continue

            return result

    def _post_json(self, payload: Dict[str, Any]) -> OpenAIResponse:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self._api_url,
            data=data,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout_s) as response:
                body = response.read().decode("utf-8")
                content = _extract_message_content(body)
                return OpenAIResponse(ok=True, content=content, status_code=response.status)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = None
            return OpenAIResponse(ok=False, content=None, status_code=exc.code, error=body)
        except Exception as exc:  # noqa: BLE001 - surface errors to caller
            return OpenAIResponse(ok=False, content=None, status_code=None, error=str(exc))


def _extract_message_content(raw_body: str) -> Optional[str]:
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return None

    choices = payload.get("choices") or []
    if not choices:
        return None

    message = choices[0].get("message") or {}
    return message.get("content")
