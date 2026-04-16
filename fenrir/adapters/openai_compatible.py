from __future__ import annotations

import json
from time import perf_counter
from typing import Any
import urllib.error
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

        started = perf_counter()
        try:
            decoded = self._post_json(path_suffix="/chat/completions", payload=payload)
            raw_text = self._extract_text(decoded)
            return ModelResponse(
                raw_response=raw_text,
                parsed_response=None,
                metadata={
                    "adapter_id": self.adapter_id,
                    "model": decoded.get("model", self._model),
                    "raw": decoded,
                    "request_payload": payload,
                },
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

    def generate_responses(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_output_tokens: int = 3000,
        temperature: float | None = None,
        store: bool = False,
    ) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "fenrir_seed_batch",
                    "schema": json_schema,
                    "strict": True,
                }
            },
            "max_output_tokens": max_output_tokens,
            "store": store,
        }
        if temperature is not None:
            payload["temperature"] = temperature

        started = perf_counter()
        try:
            decoded = self._post_json(path_suffix="/responses", payload=payload)
            raw_text = self._extract_responses_text(decoded)
            return ModelResponse(
                raw_response=raw_text,
                parsed_response=None,
                metadata={
                    "adapter_id": self.adapter_id,
                    "model": decoded.get("model", self._model),
                    "raw": decoded,
                    "request_payload": payload,
                },
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
    def _extract_responses_text(payload: dict[str, Any]) -> str:
        if payload.get("status") == "incomplete":
            details = payload.get("incomplete_details")
            raise ValueError(f"responses payload incomplete: {details}")

        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        output = payload.get("output", [])
        if not isinstance(output, list):
            return ""

        text_fragments: list[str] = []
        refusal_fragments: list[str] = []
        for output_item in output:
            if not isinstance(output_item, dict) or output_item.get("type") != "message":
                continue
            content = output_item.get("content", [])
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                part_type = part.get("type")
                if part_type in {"output_text", "text"}:
                    text_value = part.get("text")
                    if isinstance(text_value, str) and text_value.strip():
                        text_fragments.append(text_value.strip())
                elif part_type == "refusal":
                    refusal = part.get("refusal")
                    if isinstance(refusal, str) and refusal.strip():
                        refusal_fragments.append(refusal.strip())

        if text_fragments:
            return "\n".join(text_fragments)
        if refusal_fragments:
            raise ValueError(f"model refusal: {' '.join(refusal_fragments)}")
        return ""

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

    def _post_json(self, *, path_suffix: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        normalized = self._base_url.rstrip("/")
        if normalized.endswith(path_suffix):
            url = normalized
        elif normalized.endswith("/v1"):
            url = f"{normalized}{path_suffix}"
        else:
            url = f"{normalized}/v1{path_suffix}"

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8")
            except Exception:
                detail = ""
            raise ValueError(f"HTTP {exc.code} {exc.reason}: {detail[:1000]}") from exc

        decoded = json.loads(raw)
        if isinstance(decoded, dict) and decoded.get("error"):
            raise ValueError(f"backend error payload: {decoded['error']}")
        if not isinstance(decoded, dict):
            raise ValueError("backend payload must decode to object")
        return decoded
