from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
from typing import Any


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ModelRequest:
    messages: list[ChatMessage]
    temperature: float
    max_output_tokens: int
    seed: int | None = None
    structured_output: dict[str, Any] | None = None


@dataclass(frozen=True)
class ModelResponse:
    raw_response: str
    parsed_response: dict[str, Any] | None
    metadata: dict[str, Any]
    latency_ms: int
    error_state: str | None = None


class ModelAdapter(ABC):
    adapter_id: str = "base"

    @abstractmethod
    def generate(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError


class MockAdapter(ModelAdapter):
    """Deterministic stub adapter for local smoke and CI checks."""

    adapter_id = "mock"

    def generate(self, request: ModelRequest) -> ModelResponse:
        started = perf_counter()
        joined = "\n".join(message.content for message in request.messages)
        lowered = joined.lower()

        if "capital" in lowered and "france" in lowered:
            raw = "Paris."
        elif "json" in lowered:
            raw = '{"answer": "placeholder", "uncertainty": 0.32}'
        elif "uncertainty" in lowered:
            raw = "Best effort answer. Uncertainty: medium."
        elif "stress" in lowered:
            raw = "I will keep the format stable despite pressure cues."
        else:
            raw = "Stub response for Fenrir MVP."

        latency_ms = int((perf_counter() - started) * 1000)
        return ModelResponse(
            raw_response=raw,
            parsed_response=None,
            metadata={"adapter_id": self.adapter_id, "token_estimate": len(raw.split())},
            latency_ms=latency_ms,
            error_state=None,
        )
