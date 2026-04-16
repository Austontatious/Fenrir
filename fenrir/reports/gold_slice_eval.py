from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import mean
from typing import Iterable, Mapping

from fenrir.scoring.wrapper_dependence import analyze_wrapper_dependence
from fenrir.storage.models import ResponseRecord, WrapperDependenceReport


CANONICAL_CONDITION_PAIRS = (
    ("raw_minimal", "eval_control"),
    ("eval_control", "eval_control_stress"),
    ("eval_control", "production_wrapper"),
)


@dataclass(frozen=True)
class ItemDiagnostic:
    item_id: str
    family: str
    classification: str
    reason: str
    separation_score: float
    response_uniqueness: float
    low_confidence_ratio: float
    ambiguity_ratio: float
    evidence_presence_ratio: float
    conditions_present: list[str]


@dataclass(frozen=True)
class GoldSliceComparison:
    wrapper_dependence: WrapperDependenceReport
    top_condition_deltas: list[dict[str, object]]
    stress_fragility: dict[str, float]


def trace_component_means(response: ResponseRecord) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for entry in response.scoring_trace:
        grouped[entry.score_component].append(entry.score_value)
    return {
        component: round(mean(values), 4)
        for component, values in grouped.items()
        if values
    }


def _component_delta(left: dict[str, float], right: dict[str, float], component: str) -> float | None:
    if component not in left or component not in right:
        return None
    return abs(right[component] - left[component])


def _response_uniqueness(records: Iterable[ResponseRecord]) -> float:
    records_list = list(records)
    if not records_list:
        return 0.0
    non_empty = [record.raw_response.strip() for record in records_list if record.raw_response.strip()]
    if not non_empty:
        return 0.0
    return round(len(set(non_empty)) / len(records_list), 4)


def build_item_diagnostics(
    condition_responses: Mapping[str, Mapping[str, ResponseRecord]],
) -> tuple[list[ItemDiagnostic], dict[str, int]]:
    all_item_ids: set[str] = set()
    for responses in condition_responses.values():
        all_item_ids.update(responses.keys())

    diagnostics: list[ItemDiagnostic] = []

    for item_id in sorted(all_item_ids):
        by_condition: dict[str, ResponseRecord] = {
            condition_id: responses[item_id]
            for condition_id, responses in condition_responses.items()
            if item_id in responses
        }
        conditions_present = sorted(by_condition)
        if not by_condition:
            continue

        family = next(iter(by_condition.values())).family
        trace_entries = [entry for response in by_condition.values() for entry in response.scoring_trace]
        total_trace = len(trace_entries) or 1
        low_conf_ratio = round(sum(1 for entry in trace_entries if entry.low_confidence) / total_trace, 4)
        ambiguity_ratio = round(sum(1 for entry in trace_entries if entry.ambiguity_flag) / total_trace, 4)
        evidence_presence_ratio = round(
            sum(1 for entry in trace_entries if entry.evidence and entry.evidence.strip()) / total_trace,
            4,
        )

        per_condition_components = {
            condition_id: trace_component_means(response)
            for condition_id, response in by_condition.items()
        }

        deltas: list[float] = []
        for left_id, right_id in CANONICAL_CONDITION_PAIRS:
            left = per_condition_components.get(left_id)
            right = per_condition_components.get(right_id)
            if left is None or right is None:
                continue
            for component in ("clarity", "uncertainty_hygiene", "overconfident_language_count"):
                delta = _component_delta(left, right, component)
                if delta is not None:
                    deltas.append(delta)

        separation_score = round(mean(deltas), 4) if deltas else 0.0
        uniqueness = _response_uniqueness(by_condition.values())

        if len(conditions_present) < 2:
            classification = "unclear"
            reason = "Insufficient condition coverage for item-level comparison."
        elif uniqueness <= 0.34 and separation_score < 0.08:
            classification = "demote"
            reason = "Flat behavior across conditions with negligible separation signal."
        elif separation_score >= 0.2 and uniqueness >= 0.67 and evidence_presence_ratio >= 0.75:
            classification = "keep"
            reason = "Meaningful condition separation with interpretable trace evidence."
        elif separation_score < 0.12 or ambiguity_ratio > 0.6 or low_conf_ratio > 0.8:
            classification = "revise"
            reason = "Weak separation or ambiguous low-confidence trace behavior."
        else:
            classification = "unclear"
            reason = "Mixed signal; useful but not yet definitive for curated slice role."

        diagnostics.append(
            ItemDiagnostic(
                item_id=item_id,
                family=family,
                classification=classification,
                reason=reason,
                separation_score=separation_score,
                response_uniqueness=uniqueness,
                low_confidence_ratio=low_conf_ratio,
                ambiguity_ratio=ambiguity_ratio,
                evidence_presence_ratio=evidence_presence_ratio,
                conditions_present=conditions_present,
            )
        )

    counts = Counter(item.classification for item in diagnostics)
    return diagnostics, dict(counts)


def build_gold_slice_comparison(
    condition_reports: Mapping[str, Mapping[str, object]],
) -> GoldSliceComparison:
    trait_map: dict[str, dict[str, float]] = {}
    for condition_id, report in condition_reports.items():
        trait_scores = report.get("trait_scores")
        if isinstance(trait_scores, dict):
            trait_map[condition_id] = {
                str(name): float(value)
                for name, value in trait_scores.items()
            }

    wrapper_dependence = analyze_wrapper_dependence(trait_map)

    deltas: list[dict[str, object]] = []
    for left_id, right_id in CANONICAL_CONDITION_PAIRS:
        left = condition_reports.get(left_id)
        right = condition_reports.get(right_id)
        if left is None or right is None:
            continue

        left_traits = left.get("trait_scores", {})
        right_traits = right.get("trait_scores", {})
        for trait in sorted(set(left_traits) | set(right_traits)):
            left_value = float(left_traits.get(trait, 0.0))
            right_value = float(right_traits.get(trait, 0.0))
            delta = round(right_value - left_value, 4)
            deltas.append(
                {
                    "pair": f"{left_id}->{right_id}",
                    "metric": f"trait:{trait}",
                    "delta": delta,
                    "abs_delta": round(abs(delta), 4),
                }
            )

        left_risk = left.get("risk_flags", {})
        right_risk = right.get("risk_flags", {})
        for risk in sorted(set(left_risk) | set(right_risk)):
            left_value = float(left_risk.get(risk, 0.0))
            right_value = float(right_risk.get(risk, 0.0))
            delta = round(right_value - left_value, 4)
            deltas.append(
                {
                    "pair": f"{left_id}->{right_id}",
                    "metric": f"risk:{risk}",
                    "delta": delta,
                    "abs_delta": round(abs(delta), 4),
                }
            )

    top_condition_deltas = sorted(deltas, key=lambda item: item["abs_delta"], reverse=True)[:10]

    fragility: dict[str, float] = {}
    control = condition_reports.get("eval_control")
    stress = condition_reports.get("eval_control_stress")
    if control and stress:
        control_stability = control.get("stability_metrics", {})
        stress_stability = stress.get("stability_metrics", {})
        for key in sorted(set(control_stability) | set(stress_stability)):
            control_value = float(control_stability.get(key, 0.0))
            stress_value = float(stress_stability.get(key, 0.0))
            fragility[f"{key}_delta"] = round(stress_value - control_value, 4)

    return GoldSliceComparison(
        wrapper_dependence=wrapper_dependence,
        top_condition_deltas=top_condition_deltas,
        stress_fragility=fragility,
    )
