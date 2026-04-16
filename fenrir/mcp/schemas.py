from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from fenrir.orchestrator.sampling import SamplingConfig
from fenrir.orchestrator.stopping import StoppingPolicy


class RunBatteryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    battery_id: str
    condition_id: str
    model_target: str = "mock://local"
    sampling: SamplingConfig = Field(default_factory=SamplingConfig)
    stopping: StoppingPolicy = Field(default_factory=StoppingPolicy)


class CompareRunsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_run_id: str
    candidate_run_id: str


class GenerateReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    format: str = "markdown"
