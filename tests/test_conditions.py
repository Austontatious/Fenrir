from __future__ import annotations

from fenrir.conditions.registry import get_condition, list_conditions


def test_condition_registry_has_required_ids() -> None:
    ids = {item.id for item in list_conditions()}
    assert {"raw_minimal", "eval_control", "production_wrapper", "eval_control_stress"}.issubset(ids)


def test_eval_control_prompt_is_neutral_and_uncertainty_aware() -> None:
    condition = get_condition("eval_control")
    text = condition.system_prompt.lower()
    assert "neutral" in text
    assert "uncertainty" in text
