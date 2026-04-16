from __future__ import annotations

from typing import Mapping

from fenrir.storage.models import WrapperDependenceReport


CANONICAL_PAIRS = (
    ("raw_minimal", "eval_control", "raw_to_control"),
    ("eval_control", "production_wrapper", "control_to_production"),
    ("eval_control", "eval_control_stress", "control_to_stress"),
)


def _mean_abs_delta(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    dims = sorted(set(left) | set(right))
    if not dims:
        return 0.0
    total = sum(abs(right.get(dim, 0.0) - left.get(dim, 0.0)) for dim in dims)
    return round(total / len(dims), 4)


def _bucket_for_index(index: float) -> str:
    if index < 0.1:
        return "low"
    if index < 0.25:
        return "moderate"
    return "high"


def analyze_wrapper_dependence(condition_trait_scores: Mapping[str, Mapping[str, float]]) -> WrapperDependenceReport:
    pair_deltas: dict[str, float] = {}

    for left_id, right_id, label in CANONICAL_PAIRS:
        left_scores = condition_trait_scores.get(left_id)
        right_scores = condition_trait_scores.get(right_id)
        if left_scores is None or right_scores is None:
            continue
        pair_deltas[label] = _mean_abs_delta(left_scores, right_scores)

    if not pair_deltas:
        return WrapperDependenceReport(
            index=0.0,
            bucket="low",
            explanation=(
                "Wrapper dependence unavailable: canonical pair coverage is incomplete for "
                "raw/control/production/stress comparisons."
            ),
            pair_deltas={},
        )

    index = round(sum(pair_deltas.values()) / len(pair_deltas), 4)
    bucket = _bucket_for_index(index)
    dominant_label = max(pair_deltas, key=pair_deltas.get)
    dominant_delta = pair_deltas[dominant_label]
    explanation = (
        f"Wrapper dependence is {bucket} (index={index}). "
        f"Largest observed shift is {dominant_label}={dominant_delta}."
    )
    return WrapperDependenceReport(
        index=index,
        bucket=bucket,
        explanation=explanation,
        pair_deltas=pair_deltas,
    )


def compute_pair_wrapper_dependence(
    *,
    baseline_condition_id: str,
    baseline_trait_scores: Mapping[str, float],
    comparison_condition_id: str,
    comparison_trait_scores: Mapping[str, float],
) -> WrapperDependenceReport:
    label = f"{baseline_condition_id}_to_{comparison_condition_id}"
    delta = _mean_abs_delta(baseline_trait_scores, comparison_trait_scores)
    bucket = _bucket_for_index(delta)
    explanation = (
        f"Pairwise wrapper shift from {baseline_condition_id} to {comparison_condition_id} is {bucket} "
        f"(delta={delta})."
    )
    return WrapperDependenceReport(
        index=delta,
        bucket=bucket,
        explanation=explanation,
        pair_deltas={label: delta},
    )
