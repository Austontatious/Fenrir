from __future__ import annotations

from dataclasses import dataclass

from fenrir.conditions.control_prompt import (
    eval_control_prompt,
    eval_control_stress_prompt,
    production_wrapper_prompt,
    raw_minimal_prompt,
)


@dataclass(frozen=True)
class Condition:
    id: str
    description: str
    system_prompt: str
    apply_stressors: bool = False


def list_conditions(*, production_wrapper_text: str | None = None) -> list[Condition]:
    return [
        Condition(
            id="raw_minimal",
            description="Near-zero orchestration with only format sanity constraints.",
            system_prompt=raw_minimal_prompt(),
        ),
        Condition(
            id="eval_control",
            description="Neutral measurement condition for comparable runs.",
            system_prompt=eval_control_prompt(),
        ),
        Condition(
            id="production_wrapper",
            description="Production-aligned wrapper loaded from runtime configuration.",
            system_prompt=production_wrapper_prompt(production_wrapper_text),
        ),
        Condition(
            id="eval_control_stress",
            description="Control prompt with pressure/stressor cues in item rendering.",
            system_prompt=eval_control_stress_prompt(),
            apply_stressors=True,
        ),
    ]


def get_condition(condition_id: str, *, production_wrapper_text: str | None = None) -> Condition:
    for condition in list_conditions(production_wrapper_text=production_wrapper_text):
        if condition.id == condition_id:
            return condition
    raise KeyError(f"unknown condition_id: {condition_id}")
