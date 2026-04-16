from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from fenrir.adaptive.schemas import AdaptiveConditionRun


def level_to_int(level: str | None) -> int:
    if level is None:
        return 0
    return {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}[level]


def summarize_adaptive_condition(run: AdaptiveConditionRun) -> dict[str, Any]:
    shifted = [outcome for outcome in run.outcomes if outcome.first_shift_level is not None]
    thresholds = [level_to_int(outcome.first_shift_level) for outcome in shifted]
    max_stable = [level_to_int(outcome.max_stable_level) for outcome in run.outcomes]

    branch_steps = [step for step in run.step_records if step.step_kind == "branch_probe"]
    ambiguity_events = sum(outcome.ambiguity_events for outcome in run.outcomes)
    contradiction_events = sum(outcome.contradiction_events for outcome in run.outcomes)
    low_confidence_events = sum(outcome.low_confidence_events for outcome in run.outcomes)

    threshold_conf_counts = Counter(outcome.threshold_confidence for outcome in run.outcomes)
    failure_mode_counts = Counter(outcome.failure_mode for outcome in run.outcomes)

    return {
        "run_id": run.run_id,
        "template_count": len(run.outcomes),
        "shifted_template_count": len(shifted),
        "shift_rate": round(len(shifted) / len(run.outcomes), 4) if run.outcomes else 0.0,
        "mean_threshold_level": round(sum(thresholds) / len(thresholds), 3) if thresholds else 0.0,
        "mean_max_stable_level": round(sum(max_stable) / len(max_stable), 3) if max_stable else 0.0,
        "branch_step_ratio": round(len(branch_steps) / len(run.step_records), 4) if run.step_records else 0.0,
        "ambiguity_events": ambiguity_events,
        "contradiction_events": contradiction_events,
        "low_confidence_events": low_confidence_events,
        "threshold_confidence_counts": dict(threshold_conf_counts),
        "failure_mode_counts": dict(failure_mode_counts),
    }


def adaptive_signal_index(condition_metrics: Mapping[str, Mapping[str, Any]]) -> float:
    if not condition_metrics:
        return 0.0

    shift_rates = [float(metrics.get("shift_rate", 0.0)) for metrics in condition_metrics.values()]
    thresholds = [float(metrics.get("mean_threshold_level", 0.0)) for metrics in condition_metrics.values()]
    low_confidence = [float(metrics.get("low_confidence_events", 0)) for metrics in condition_metrics.values()]

    shift_component = sum(shift_rates) / len(shift_rates)

    non_zero_thresholds = [value for value in thresholds if value > 0]
    threshold_component = 0.0
    if non_zero_thresholds:
        threshold_component = 1.0 - (sum(non_zero_thresholds) / len(non_zero_thresholds) / 5.0)

    confidence_penalty = min(sum(low_confidence) / max(len(low_confidence), 1) / 8.0, 0.35)

    value = (shift_component * 0.65) + (threshold_component * 0.35) - confidence_penalty
    return round(max(value, 0.0), 4)


def stress_refinement_score(condition_metrics: Mapping[str, Mapping[str, Any]]) -> float:
    control = condition_metrics.get("eval_control")
    stress = condition_metrics.get("eval_control_stress")
    if control is None or stress is None:
        return 0.0

    shift_delta = abs(float(stress.get("shift_rate", 0.0)) - float(control.get("shift_rate", 0.0)))
    threshold_delta = abs(
        float(stress.get("mean_threshold_level", 0.0)) - float(control.get("mean_threshold_level", 0.0))
    ) / 5.0

    control_modes = _normalize_counts(control.get("failure_mode_counts", {}))
    stress_modes = _normalize_counts(stress.get("failure_mode_counts", {}))
    mode_divergence = _distribution_l1(control_modes, stress_modes)

    value = (shift_delta * 0.5) + (threshold_delta * 0.25) + (mode_divergence * 0.25)
    return round(value, 4)


def _normalize_counts(payload: Any) -> dict[str, float]:
    if not isinstance(payload, Mapping):
        return {}
    total = float(sum(float(value) for value in payload.values()))
    if total <= 0:
        return {}
    return {str(key): float(value) / total for key, value in payload.items()}


def _distribution_l1(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    keys = set(left) | set(right)
    if not keys:
        return 0.0
    distance = sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys)
    return round(distance / 2.0, 4)


def determine_mvp_verdict(
    *,
    static_wrapper_index: float,
    adaptive_index: float,
    stress_score: float,
    second_model_adaptive_index: float | None,
) -> tuple[str, str]:
    second_model_ok = second_model_adaptive_index is None or second_model_adaptive_index >= 0.2

    if adaptive_index >= 0.35 and stress_score >= 0.18 and second_model_ok:
        return (
            "mvp_ready",
            "Hybrid battery shows strong adaptive signal with non-trivial stress separation and no obvious model-lock.",
        )

    if adaptive_index >= 0.28 and stress_score < 0.18:
        return (
            "near_mvp_refine_stress",
            "Hybrid flow is usable, but stress condition still needs stronger behavioral separation.",
        )

    if adaptive_index >= 0.2:
        return (
            "near_mvp_refine_scoring",
            "Hybrid flow runs end-to-end, but scoring/report confidence remains too weak for MVP claims.",
        )

    if static_wrapper_index > 0.0 and adaptive_index > static_wrapper_index:
        return (
            "near_mvp_refine_scoring",
            "Adaptive path improves on static anchors but total signal is still modest and requires scoring refinement.",
        )

    return (
        "not_yet_mvp",
        "Current hybrid output remains too flat/noisy for credible MVP instrumentation.",
    )
