from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ADAPTIVE_TEMPLATE_SCHEMA_VERSION = "fenrir.adaptive.template.v0"
ADAPTIVE_RUN_SCHEMA_VERSION = "fenrir.adaptive.run.v0"
ADAPTIVE_EVAL_SCHEMA_VERSION = "fenrir.adaptive.eval.v0"


LadderLevelId = Literal["L1", "L2", "L3", "L4", "L5"]
NextAction = Literal["escalate", "branch_probe", "stop"]
DecisionReason = Literal[
    "stable_no_signal",
    "ambiguity",
    "contradiction",
    "threshold_crossed",
    "max_depth",
    "branch_resolved",
]
FailureMode = Literal[
    "concealment",
    "confidence_smoothing",
    "approval_seeking",
    "authority_compliance",
    "reputational_shielding",
    "none_observed",
]


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class AdaptiveLadderLevel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level_id: LadderLevelId
    description: str
    pressure_instruction: str


class AdaptiveTemplateFamily(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[ADAPTIVE_TEMPLATE_SCHEMA_VERSION] = ADAPTIVE_TEMPLATE_SCHEMA_VERSION
    template_id: str
    template_version: str
    family: str
    dimension: str
    description: str
    base_prompt_template: str
    options: dict[str, str]
    stable_option: Literal["A", "B"]
    pressure_option: Literal["A", "B"]
    slots: dict[str, list[str]]
    ladder: list[AdaptiveLadderLevel]
    branch_probe_template: str


class AdaptiveProbeInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    probe_id: str
    template_id: str
    template_version: str
    family: str
    dimension: str
    ladder_level: LadderLevelId
    slots: dict[str, str]
    prompt_text: str
    stable_option: Literal["A", "B"]
    pressure_option: Literal["A", "B"]
    provenance: dict[str, Any]


class AdaptiveResponseFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_option: Literal["A", "B"] | None = None
    ambiguity: bool = False
    contradiction: bool = False
    shift_detected: bool = False
    concealment_markers: int = 0
    approval_markers: int = 0
    authority_markers: int = 0
    confidence_smoothing_markers: int = 0
    failure_mode: FailureMode = "none_observed"


class AdaptiveDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    next_action: NextAction
    reason: DecisionReason
    next_level: LadderLevelId | None = None


class AdaptiveStepRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_index: int
    ladder_level: LadderLevelId
    step_kind: Literal["primary", "branch_probe"]
    prompt_text: str
    response_text: str
    adapter_metadata: dict[str, Any]
    latency_ms: int
    features: AdaptiveResponseFeatures
    decision: AdaptiveDecision


class AdaptiveTemplateOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    template_version: str
    family: str
    dimension: str
    pressure_threshold: LadderLevelId | None = None
    max_stable_level: LadderLevelId | None = None
    first_shift_level: LadderLevelId | None = None
    failure_mode: FailureMode = "none_observed"
    stop_reason: DecisionReason
    step_count: int


class AdaptiveConditionRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[ADAPTIVE_RUN_SCHEMA_VERSION] = ADAPTIVE_RUN_SCHEMA_VERSION
    run_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    model_target: str
    model_adapter: str
    condition_id: str
    condition_version: str
    condition_provenance: dict[str, Any]
    template_count: int
    outcomes: list[AdaptiveTemplateOutcome]
    step_records: list[AdaptiveStepRecord]


class AdaptiveEvalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[ADAPTIVE_EVAL_SCHEMA_VERSION] = ADAPTIVE_EVAL_SCHEMA_VERSION
    eval_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    model_target: str
    adapter_id: str
    conditions_run: list[str]
    template_families: list[str]
    dimensions: list[str]
    condition_metrics: dict[str, dict[str, Any]]
    adaptive_signal_index: float
    static_signal_index: float | None = None
    comparison_note: str
    recommendation: Literal[
        "continue_adaptive",
        "hybridize",
        "revise_adaptive_templates",
        "pause_adaptive",
    ]
    caveats: list[str]
