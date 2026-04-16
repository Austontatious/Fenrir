from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from fenrir.conditions.control_prompt import (
    eval_control_prompt,
    eval_control_stress_prompt,
    production_wrapper_prompt,
    prompt_path,
    raw_minimal_prompt,
)
from fenrir.storage.models import ConditionProvenance


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _source_for_prompt(name: str) -> str:
    path = prompt_path(name)
    repo_root = Path(__file__).resolve().parents[2]
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


@dataclass(frozen=True)
class Condition:
    id: str
    version: str
    description: str
    system_prompt: str
    system_prompt_source: str
    prompt_template_version: str
    system_prompt_hash: str
    inline_prompt_hash: str | None = None
    apply_stressors: bool = False
    stress_profile_id: str | None = None
    stress_profile_version: str | None = None
    production_wrapper_source: str | None = None

    def to_provenance(self) -> ConditionProvenance:
        return ConditionProvenance(
            condition_id=self.id,
            condition_version=self.version,
            system_prompt_source=self.system_prompt_source,
            system_prompt_hash=self.system_prompt_hash,
            prompt_template_version=self.prompt_template_version,
            inline_prompt_hash=self.inline_prompt_hash,
            stress_profile_id=self.stress_profile_id,
            stress_profile_version=self.stress_profile_version,
            production_wrapper_source=self.production_wrapper_source,
        )


def list_conditions(
    *,
    production_wrapper_text: str | None = None,
    production_wrapper_source: str | None = None,
) -> list[Condition]:
    raw_prompt = raw_minimal_prompt()
    control_prompt = eval_control_prompt()
    stress_prompt = eval_control_stress_prompt()

    static_source = _source_for_prompt("fenrir_production_wrapper_placeholder")
    prod_prompt = production_wrapper_prompt(production_wrapper_text)
    if production_wrapper_text and production_wrapper_text.strip():
        prod_source = "inline:production_wrapper"
        inline_hash = _sha256_text(prod_prompt)
        prod_source_id = production_wrapper_source or "runtime:inline"
    else:
        prod_source = static_source
        inline_hash = None
        prod_source_id = production_wrapper_source or static_source

    return [
        Condition(
            id="raw_minimal",
            version="1.0.0",
            description="Near-zero orchestration with only format sanity constraints.",
            system_prompt=raw_prompt,
            system_prompt_source=_source_for_prompt("fenrir_raw_minimal"),
            prompt_template_version="raw_minimal.prompt.v1",
            system_prompt_hash=_sha256_text(raw_prompt),
        ),
        Condition(
            id="eval_control",
            version="1.0.0",
            description="Neutral measurement condition for comparable runs.",
            system_prompt=control_prompt,
            system_prompt_source=_source_for_prompt("fenrir_eval_control"),
            prompt_template_version="eval_control.prompt.v1",
            system_prompt_hash=_sha256_text(control_prompt),
        ),
        Condition(
            id="production_wrapper",
            version="1.0.0",
            description="Production-aligned wrapper loaded from runtime configuration.",
            system_prompt=prod_prompt,
            system_prompt_source=prod_source,
            prompt_template_version="production_wrapper.prompt.v1",
            system_prompt_hash=_sha256_text(prod_prompt),
            inline_prompt_hash=inline_hash,
            production_wrapper_source=prod_source_id,
        ),
        Condition(
            id="eval_control_stress",
            version="1.0.0",
            description="Control prompt with pressure/stressor cues in item rendering.",
            system_prompt=stress_prompt,
            system_prompt_source=_source_for_prompt("fenrir_eval_control_stress"),
            prompt_template_version="eval_control_stress.prompt.v1",
            system_prompt_hash=_sha256_text(stress_prompt),
            apply_stressors=True,
            stress_profile_id="default_stress_profile",
            stress_profile_version="1.0.0",
        ),
    ]


def get_condition(
    condition_id: str,
    *,
    production_wrapper_text: str | None = None,
    production_wrapper_source: str | None = None,
) -> Condition:
    for condition in list_conditions(
        production_wrapper_text=production_wrapper_text,
        production_wrapper_source=production_wrapper_source,
    ):
        if condition.id == condition_id:
            return condition
    raise KeyError(f"unknown condition_id: {condition_id}")
