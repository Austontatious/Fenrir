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
    assert condition.version == "1.0.0"
    assert condition.system_prompt_source.endswith("fenrir_eval_control.md")
    assert len(condition.system_prompt_hash) == 64


def test_inline_production_wrapper_records_inline_hash() -> None:
    condition = get_condition(
        "production_wrapper",
        production_wrapper_text="Use strict production guardrails.",
        production_wrapper_source="config://prod-wrapper-v1",
    )
    assert condition.system_prompt_source == "inline:production_wrapper"
    assert condition.inline_prompt_hash is not None
    assert condition.production_wrapper_source == "config://prod-wrapper-v1"
