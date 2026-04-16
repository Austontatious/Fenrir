from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SamplingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperature: float = 0.2
    max_output_tokens: int = 220
    seed: int | None = None
    structured_output: bool = False
