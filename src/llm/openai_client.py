"""Minimal OpenAI client for chat completions."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class OpenAIClient:
    """Minimal OpenAI HTTP client with basic retry support."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: int = 30,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is missing.")
        if not model:
            raise ValueError("OpenAI model is missing.")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._base_url = base_url.rstrip("/")

    @property
    def model(self) -> str:
        return self._model

    def create_chat_completion(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.2,
        }
        url = f"{self._base_url}/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(2):
            request = urllib.request.Request(url, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    body = response.read().decode("utf-8")
                return self._extract_message(body)
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8") if exc.fp else ""
                if exc.code in (429,) or 500 <= exc.code <= 599:
                    if attempt == 0:
                        time.sleep(1.0)
                        continue
                raise RuntimeError(f"OpenAI API error {exc.code}: {body}") from exc
            except urllib.error.URLError as exc:
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                raise RuntimeError(f"OpenAI API request failed: {exc}") from exc

        raise RuntimeError("OpenAI API request failed after retry.")

    @staticmethod
    def _extract_message(body: str) -> str:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenAI API returned invalid JSON.") from exc
        choices = payload.get("choices")
        if not choices:
            raise RuntimeError("OpenAI API returned no choices.")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("OpenAI API returned empty content.")
        return content
