from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from fenrir import __version__ as fenrir_version
from fenrir.orchestrator.sampling import SamplingConfig
from fenrir.orchestrator.stopping import StoppingPolicy


RUN_MANIFEST_SCHEMA_VERSION = "fenrir.run_manifest.v1"
RESPONSE_RECORD_SCHEMA_VERSION = "fenrir.response_record.v1"
REPORT_SCHEMA_VERSION = "fenrir.report.v1"
REPORT_VERSION = "1.0.0"


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


class ConditionProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_id: str
    condition_version: str
    system_prompt_source: str
    system_prompt_hash: str
    prompt_template_version: str
    inline_prompt_hash: str | None = None
    stress_profile_id: str | None = None
    stress_profile_version: str | None = None
    production_wrapper_source: str | None = None


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[RUN_MANIFEST_SCHEMA_VERSION] = RUN_MANIFEST_SCHEMA_VERSION
    run_id: str
    battery_id: str
    battery_version: str
    model_target: str
    model_adapter: str
    condition_id: str
    condition_version: str
    system_prompt_hash: str
    system_prompt_source: str
    stress_profile_id: str | None = None
    sampling_config: SamplingConfig
    stopping_policy: StoppingPolicy
    selected_item_ids: list[str]
    created_at: str = Field(default_factory=utc_now_iso)
    fenrir_version: str = fenrir_version


class ScoringTraceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rubric_id: str
    score_component: str
    triggered_feature: str
    score_value: float
    contradiction_flag: bool = False
    ambiguity_flag: bool = False
    low_confidence: bool = True
    evidence: str | None = None


class ResponseProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    battery_version: str
    item_version: str
    model_target: str
    model_adapter: str
    response_schema_ref: str
    system_prompt_source: str
    system_prompt_hash: str
    prompt_template_version: str
    stress_profile_id: str | None = None
    production_wrapper_source: str | None = None


class ResponseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[RESPONSE_RECORD_SCHEMA_VERSION] = RESPONSE_RECORD_SCHEMA_VERSION
    run_id: str
    item_id: str
    family: str
    condition_id: str
    condition_version: str
    raw_response: str
    parsed_response: dict[str, Any] | None
    adapter_metadata: dict[str, Any]
    latency_ms: int
    temperature: float
    seed: int | None
    error_state: str | None = None
    scoring_trace: list[ScoringTraceEntry] = Field(default_factory=list)
    provenance: ResponseProvenance


class WrapperDependenceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: float
    bucket: Literal["low", "moderate", "high"]
    explanation: str
    pair_deltas: dict[str, float] = Field(default_factory=dict)


class ReportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[REPORT_SCHEMA_VERSION] = REPORT_SCHEMA_VERSION
    run_id: str
    summary: str
    trait_scores: dict[str, float]
    risk_flags: dict[str, int]
    stability_metrics: dict[str, float]
    wrapper_dependence: WrapperDependenceReport
    contradictions: list[str]
    coverage: dict[str, Any]
    condition_provenance: ConditionProvenance
    caveats: list[str]
    prohibited_inferences: list[str]
    report_version: str = REPORT_VERSION


def artifact_json_schemas() -> dict[str, dict[str, Any]]:
    return {
        "run_manifest": RunManifest.model_json_schema(),
        "response_record": ResponseRecord.model_json_schema(),
        "report": ReportRecord.model_json_schema(),
    }


def write_artifact_json_schemas(schema_root: Path) -> dict[str, Path]:
    schema_root.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, schema in artifact_json_schemas().items():
        path = schema_root / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = path
    return written
