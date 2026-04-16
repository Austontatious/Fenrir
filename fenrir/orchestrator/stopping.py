from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StoppingPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_items: int = 5
    stop_on_error_rate: float = 1.0
