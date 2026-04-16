from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fenrir.orchestrator.sampling import SamplingConfig
from fenrir.orchestrator.stopping import StoppingPolicy


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


class ItemRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    battery_id: str
    version: str
    family: str
    target_dimensions: list[str]
    prompt: str
    response_schema_ref: str
    scoring_refs: list[str]
    difficulty: str
    sensitivity_tags: list[str] = Field(default_factory=list)
    variant_group: str | None = None
    notes: str = ""


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    battery_id: str
    battery_version: str
    model_target: str
    condition_id: str
    sampling_config: SamplingConfig
    stopping_policy: StoppingPolicy
    selected_items: list[str]
    created_at: str = Field(default_factory=utc_now_iso)


class ResponseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    raw_response: str
    parsed_response: dict[str, Any] | None
    adapter_metadata: dict[str, Any]
    latency_ms: int
    condition_id: str
    temperature: float
    seed: int | None
    error_state: str | None = None


class ReportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    summary: str
    trait_scores: dict[str, float]
    risk_flags: dict[str, int]
    stability_metrics: dict[str, float]
    wrapper_dependence: dict[str, float]
    contradictions: list[str]
    coverage: dict[str, Any]
    caveats: list[str]
    prohibited_inferences: list[str]
