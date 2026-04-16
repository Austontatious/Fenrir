from __future__ import annotations

import json
from time import perf_counter
from typing import Any
import urllib.request

from fenrir.adapters.base import ChatMessage, ModelAdapter, ModelRequest, ModelResponse


class OpenAICompatibleAdapter(ModelAdapter):
    """Thin adapter for OpenAI-compatible chat completion endpoints."""

    adapter_id = "openai_compatible"

    def __init__(self, *, base_url: str, model: str, api_key: str = "", timeout_seconds: float = 45.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def generate(self, request: ModelRequest) -> ModelResponse:
        payload = {
            "model": self._model,
            "messages": [self._message_to_dict(message) for message in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        if request.structured_output is not None:
            payload["response_format"] = request.structured_output

        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        url = f"{self._base_url}/chat/completions" if not self._base_url.endswith("/chat/completions") else self._base_url
        started = perf_counter()
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self._timeout_seconds) as response:
                decoded = json.loads(response.read().decode("utf-8"))
            raw_text = self._extract_text(decoded)
            return ModelResponse(
                raw_response=raw_text,
                parsed_response=None,
                metadata={"adapter_id": self.adapter_id, "model": decoded.get("model", self._model), "raw": decoded},
                latency_ms=int((perf_counter() - started) * 1000),
                error_state=None,
            )
        except Exception as exc:  # pragma: no cover - network failures are environment-specific.
            return ModelResponse(
                raw_response="",
                parsed_response=None,
                metadata={"adapter_id": self.adapter_id, "model": self._model},
                latency_ms=int((perf_counter() - started) * 1000),
                error_state=str(exc),
            )

    @staticmethod
    def _message_to_dict(message: ChatMessage) -> dict[str, str]:
        return {"role": message.role, "content": message.content}

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        choices = payload.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [piece.get("text", "") for piece in content if isinstance(piece, dict)]
            return "".join(parts).strip()
        return ""
