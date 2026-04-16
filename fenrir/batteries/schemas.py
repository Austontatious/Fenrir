from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ItemFamily = Literal["trait", "sjt", "redteam", "consistency_probe", "paraphrase"]


class BatteryMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    version: str
    description: str
    intended_use: str
    prohibited_claims: list[str] = Field(default_factory=list)


class BatteryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    battery_id: str
    version: str
    family: ItemFamily
    target_dimensions: list[str]
    prompt: str
    response_schema_ref: str
    scoring_refs: list[str]
    difficulty: str
    sensitivity_tags: list[str] = Field(default_factory=list)
    variant_group: str | None = None
    notes: str = ""


class BatterySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "fenrir.battery.v1"
    metadata: BatteryMetadata
    dimensions: list[str]
    item_families: list[str]
    response_format: dict[str, str] = Field(default_factory=dict)
    scoring_map: dict[str, str] = Field(default_factory=dict)
    condition_compatibility: list[str]
    stopping_policy_defaults: dict[str, int | float | str]
    item_files: list[str]


class LoadedBattery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec: BatterySpec
    items: list[BatteryItem]
