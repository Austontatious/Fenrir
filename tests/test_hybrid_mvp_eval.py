from __future__ import annotations

from fenrir.adaptive.schemas import (
    AdaptiveConditionRun,
    AdaptiveDecision,
    AdaptiveResponseFeatures,
    AdaptiveStepRecord,
    AdaptiveTemplateOutcome,
)
from fenrir.reports.hybrid_mvp import (
    adaptive_signal_components,
    determine_mvp_verdict,
    stress_refinement_score,
    summarize_adaptive_condition,
)


def _adaptive_run(
    *,
    condition_id: str,
    shift_level: str | None,
    failure_mode: str,
    ambiguity_events: int = 0,
    low_confidence_events: int = 0,
) -> AdaptiveConditionRun:
    outcome = AdaptiveTemplateOutcome(
        template_id="adaptive_test",
        template_version="0.1.0",
        family="reputation_shielding",
        dimension="transparency_vs_concealment",
        pressure_threshold=shift_level,
        max_stable_level="L2" if shift_level else "L5",
        first_shift_level=shift_level,
        threshold_confidence="medium",
        failure_mode=failure_mode,
        failure_mode_reason="test reason",
        ambiguity_events=ambiguity_events,
        contradiction_events=0,
        low_confidence_events=low_confidence_events,
        stop_reason="threshold_crossed" if shift_level else "max_depth",
        step_count=3,
    )
    step = AdaptiveStepRecord(
        step_index=1,
        ladder_level="L2",
        step_kind="primary",
        prompt_text="prompt",
        response_text="option_key: A",
        adapter_metadata={},
        latency_ms=10,
        stress_overlay=[],
        features=AdaptiveResponseFeatures(
            selected_option="A",
            ambiguity=False,
            contradiction=False,
            shift_detected=bool(shift_level),
            failure_mode=failure_mode,
            failure_mode_reason="test reason",
            label_confidence="medium",
            confidence_note="test note",
            evidence_markers=["selected_option:A"],
        ),
        decision=AdaptiveDecision(next_action="stop", reason="max_depth", next_level=None),
    )
    return AdaptiveConditionRun(
        run_id=f"run-{condition_id}",
        model_target="test://model",
        model_adapter="mock",
        condition_id=condition_id,
        condition_version="1.0.0",
        condition_provenance={
            "condition_id": condition_id,
            "condition_version": "1.0.0",
            "system_prompt_source": "prompts/system/fenrir_eval_control.md",
            "system_prompt_hash": "abc",
            "prompt_template_version": "eval_control.prompt.v1",
            "inline_prompt_hash": None,
            "stress_profile_id": None,
            "stress_profile_version": None,
            "production_wrapper_source": None,
        },
        template_count=1,
        outcomes=[outcome],
        step_records=[step],
    )


def test_summarize_adaptive_condition_exposes_threshold_and_failure_counts() -> None:
    run = _adaptive_run(
        condition_id="eval_control",
        shift_level="L3",
        failure_mode="reputational_shielding",
        ambiguity_events=1,
        low_confidence_events=1,
    )
    metrics = summarize_adaptive_condition(run)

    assert metrics["template_count"] == 1
    assert metrics["shifted_template_count"] == 1
    assert metrics["mean_threshold_level"] == 3.0
    assert metrics["failure_mode_counts"]["reputational_shielding"] == 1


def test_stress_refinement_score_reflects_control_stress_divergence() -> None:
    score = stress_refinement_score(
        {
            "eval_control": {
                "shift_rate": 0.1,
                "mean_threshold_level": 4.0,
                "failure_mode_counts": {"no_material_shift": 4},
            },
            "eval_control_stress": {
                "shift_rate": 0.7,
                "mean_threshold_level": 2.0,
                "failure_mode_counts": {"reputational_shielding": 2, "policy_softening": 2},
            },
        }
    )

    assert score > 0.2


def test_adaptive_signal_index_penalizes_low_confidence_events() -> None:
    high = adaptive_signal_components(
        {
            "raw_minimal": {
                "shift_rate": 0.8,
                "mean_threshold_level": 2.0,
                "low_confidence_informative_ratio": 0.0,
                "threshold_low_confidence_ratio": 0.0,
                "template_count": 3,
                "shifted_template_count": 3,
                "branch_step_ratio": 0.2,
                "failure_mode_counts": {"authority_compliance": 2, "no_material_shift": 1},
                "no_material_shift_ratio": 0.3333,
                "ambiguity_events": 0,
                "contradiction_events": 0,
            }
        }
    )["confidence_adjusted_signal_index"]
    low = adaptive_signal_components(
        {
            "raw_minimal": {
                "shift_rate": 0.8,
                "mean_threshold_level": 2.0,
                "low_confidence_informative_ratio": 1.0,
                "threshold_low_confidence_ratio": 1.0,
                "template_count": 3,
                "shifted_template_count": 3,
                "branch_step_ratio": 0.2,
                "failure_mode_counts": {"authority_compliance": 2, "no_material_shift": 1},
                "no_material_shift_ratio": 0.3333,
                "ambiguity_events": 2,
                "contradiction_events": 2,
            }
        }
    )["confidence_adjusted_signal_index"]

    assert high > low


def test_determine_mvp_verdict_prefers_refine_stress_when_stress_is_weak() -> None:
    verdict, rationale = determine_mvp_verdict(
        static_wrapper_index=0.0,
        adaptive_raw_index=0.4,
        adaptive_adjusted_index=0.24,
        uncertainty_penalty_index=0.18,
        stress_score=0.08,
        second_model_adaptive_adjusted_index=None,
    )

    assert verdict == "near_mvp_refine_templates"
    assert "stress" in rationale.lower() or "template" in rationale.lower()
