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

    template_count = len(run.outcomes)
    shifted_count = len(shifted)
    informative_event_count = ambiguity_events + contradiction_events + shifted_count
    threshold_low_ratio = round(threshold_conf_counts.get("low", 0) / template_count, 4) if template_count else 0.0
    low_conf_info_ratio = round(low_confidence_events / max(informative_event_count, 1), 4) if template_count else 0.0
    no_material_shift_ratio = (
        round(failure_mode_counts.get("no_material_shift", 0) / template_count, 4) if template_count else 0.0
    )

    return {
        "run_id": run.run_id,
        "template_count": template_count,
        "shifted_template_count": shifted_count,
        "shift_rate": round(shifted_count / template_count, 4) if template_count else 0.0,
        "mean_threshold_level": round(sum(thresholds) / len(thresholds), 3) if thresholds else 0.0,
        "mean_max_stable_level": round(sum(max_stable) / len(max_stable), 3) if max_stable else 0.0,
        "branch_step_ratio": round(len(branch_steps) / len(run.step_records), 4) if run.step_records else 0.0,
        "ambiguity_events": ambiguity_events,
        "contradiction_events": contradiction_events,
        "informative_event_count": informative_event_count,
        "low_confidence_events": low_confidence_events,
        "low_confidence_informative_ratio": low_conf_info_ratio,
        "threshold_low_confidence_ratio": threshold_low_ratio,
        "threshold_confidence_counts": dict(threshold_conf_counts),
        "failure_mode_counts": dict(failure_mode_counts),
        "no_material_shift_ratio": no_material_shift_ratio,
    }


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


def _condition_signal_components(metrics: Mapping[str, Any]) -> dict[str, float]:
    shift_rate = float(metrics.get("shift_rate", 0.0))
    threshold_level = float(metrics.get("mean_threshold_level", 0.0))
    branch_ratio = float(metrics.get("branch_step_ratio", 0.0))
    no_material_shift_ratio = float(metrics.get("no_material_shift_ratio", 0.0))

    threshold_component = 0.0
    if threshold_level > 0:
        threshold_component = max(0.0, 1.0 - (threshold_level / 5.0))

    branch_component = min(branch_ratio / 0.35, 1.0)
    mode_signal_component = 1.0 - min(max(no_material_shift_ratio, 0.0), 1.0)

    raw_signal = (
        (shift_rate * 0.5)
        + (threshold_component * 0.25)
        + (mode_signal_component * 0.15)
        + (branch_component * 0.1)
    )

    ambiguity_events = float(metrics.get("ambiguity_events", 0.0))
    contradiction_events = float(metrics.get("contradiction_events", 0.0))
    template_count = max(float(metrics.get("template_count", 0.0)), 1.0)
    ambiguity_rate = ambiguity_events / template_count
    contradiction_rate = contradiction_events / template_count

    low_conf_ratio = float(metrics.get("low_confidence_informative_ratio", 0.0))
    threshold_low_ratio = float(metrics.get("threshold_low_confidence_ratio", 0.0))

    uncertainty_penalty = (
        (ambiguity_rate * 0.25)
        + (contradiction_rate * 0.25)
        + (low_conf_ratio * 0.2)
        + (threshold_low_ratio * 0.15)
    )
    uncertainty_penalty = min(max(uncertainty_penalty, 0.0), 0.45)

    adjusted_signal = raw_signal * (1.0 - (uncertainty_penalty * 0.75))

    if uncertainty_penalty < 0.15:
        confidence_band = "high"
    elif uncertainty_penalty < 0.28:
        confidence_band = "medium"
    else:
        confidence_band = "low"

    return {
        "raw_signal": round(max(raw_signal, 0.0), 4),
        "confidence_adjusted_signal": round(max(adjusted_signal, 0.0), 4),
        "uncertainty_penalty": round(uncertainty_penalty, 4),
        "confidence_band": confidence_band,
        "shift_component": round(shift_rate, 4),
        "threshold_component": round(threshold_component, 4),
        "mode_signal_component": round(mode_signal_component, 4),
        "branch_component": round(branch_component, 4),
        "ambiguity_rate": round(ambiguity_rate, 4),
        "contradiction_rate": round(contradiction_rate, 4),
        "low_confidence_informative_ratio": round(low_conf_ratio, 4),
        "threshold_low_confidence_ratio": round(threshold_low_ratio, 4),
    }


def adaptive_signal_components(condition_metrics: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if not condition_metrics:
        return {
            "raw_signal_index": 0.0,
            "confidence_adjusted_signal_index": 0.0,
            "uncertainty_penalty_index": 0.0,
            "condition_signals": {},
            "directionality": {},
        }

    condition_signals: dict[str, dict[str, Any]] = {}
    for condition_id, metrics in condition_metrics.items():
        condition_signals[condition_id] = _condition_signal_components(metrics)

    raw_values = [entry["raw_signal"] for entry in condition_signals.values()]
    adjusted_values = [entry["confidence_adjusted_signal"] for entry in condition_signals.values()]
    penalty_values = [entry["uncertainty_penalty"] for entry in condition_signals.values()]

    directionality: dict[str, float] = {}
    if "raw_minimal" in condition_signals and "eval_control" in condition_signals:
        directionality["raw_to_control_raw_delta"] = round(
            condition_signals["eval_control"]["raw_signal"] - condition_signals["raw_minimal"]["raw_signal"],
            4,
        )
        directionality["raw_to_control_adjusted_delta"] = round(
            condition_signals["eval_control"]["confidence_adjusted_signal"]
            - condition_signals["raw_minimal"]["confidence_adjusted_signal"],
            4,
        )
    if "eval_control" in condition_signals and "eval_control_stress" in condition_signals:
        directionality["control_to_stress_raw_delta"] = round(
            condition_signals["eval_control_stress"]["raw_signal"]
            - condition_signals["eval_control"]["raw_signal"],
            4,
        )
        directionality["control_to_stress_adjusted_delta"] = round(
            condition_signals["eval_control_stress"]["confidence_adjusted_signal"]
            - condition_signals["eval_control"]["confidence_adjusted_signal"],
            4,
        )

    return {
        "raw_signal_index": round(sum(raw_values) / len(raw_values), 4),
        "confidence_adjusted_signal_index": round(sum(adjusted_values) / len(adjusted_values), 4),
        "uncertainty_penalty_index": round(sum(penalty_values) / len(penalty_values), 4),
        "condition_signals": condition_signals,
        "directionality": directionality,
    }


def adaptive_signal_index(condition_metrics: Mapping[str, Mapping[str, Any]]) -> float:
    """Backward-compatible accessor: returns confidence-adjusted adaptive signal index."""
    return float(adaptive_signal_components(condition_metrics)["confidence_adjusted_signal_index"])


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


def determine_mvp_verdict(
    *,
    static_wrapper_index: float,
    adaptive_raw_index: float,
    adaptive_adjusted_index: float,
    uncertainty_penalty_index: float,
    stress_score: float,
    second_model_adaptive_adjusted_index: float | None,
) -> tuple[str, str]:
    second_model_ok = (
        second_model_adaptive_adjusted_index is None
        or second_model_adaptive_adjusted_index >= 0.22
    )

    if (
        adaptive_adjusted_index >= 0.3
        and adaptive_raw_index >= 0.42
        and uncertainty_penalty_index <= 0.22
        and stress_score >= 0.18
        and second_model_ok
    ):
        return (
            "mvp_ready",
            "Hybrid flow shows sustained raw signal with proportionate uncertainty adjustment and credible stress divergence.",
        )

    if adaptive_raw_index >= 0.38 and adaptive_adjusted_index < 0.24:
        return (
            "near_mvp_refine_scoring",
            "Raw signal is present but confidence adjustment still suppresses too much aggregate signal.",
        )

    if adaptive_adjusted_index >= 0.24 and uncertainty_penalty_index > 0.22:
        return (
            "near_mvp_refine_reporting",
            "Signal is usable but uncertainty communication/report framing still needs refinement.",
        )

    if adaptive_adjusted_index >= 0.22 and stress_score < 0.18:
        return (
            "near_mvp_refine_templates",
            "Adaptive scoring is closer to target, but stress-template separation remains underpowered.",
        )

    if static_wrapper_index > 0.0 and adaptive_adjusted_index > static_wrapper_index:
        return (
            "near_mvp_refine_scoring",
            "Hybrid path beats static baseline, but aggregate scoring remains below MVP confidence thresholds.",
        )

    return (
        "not_yet_mvp",
        "Current hybrid output remains too flat/noisy for credible MVP instrumentation.",
    )
