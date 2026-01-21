"""OpenAI API client implementation."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from urllib import error as url_error
from urllib import request

from .client import LLMClient, LLMUnavailableError


class OpenAIClient(LLMClient):
    """OpenAI Chat Completions client."""

    def __init__(self, *, timeout_s: float = 15.0, temperature: float = 0.1) -> None:
        self._api_key = os.getenv("OPENAI_API_KEY")
        self._model = os.getenv("OPENAI_MODEL")
        self._timeout_s = timeout_s
        self._temperature = temperature

        if not self._api_key or not self._model:
            raise LLMUnavailableError("Missing OpenAI API key or model.")

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        system_prompt: str,
        user_payload: str,
        response_format: Optional[dict] = None,
    ) -> str:
        payload = {
            "model": self._model,
            "temperature": self._temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ],
        }
        if response_format:
            payload["response_format"] = response_format
        body = json.dumps(payload).encode("utf-8")
        url = "https://api.openai.com/v1/chat/completions"
        request_obj = request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(request_obj, timeout=self._timeout_s) as response:
                raw = response.read().decode("utf-8")
        except (url_error.HTTPError, url_error.URLError, TimeoutError) as exc:
            raise LLMUnavailableError("OpenAI request failed.") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMUnavailableError("OpenAI returned invalid JSON.") from exc

        content = _extract_chat_content(parsed)
        if content is None:
            raise LLMUnavailableError("OpenAI response missing content.")
        return content


def _extract_chat_content(payload: Dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    return content if isinstance(content, str) else None
