from __future__ import annotations


def compute_wrapper_dependence(
    baseline_trait_scores: dict[str, float],
    comparison_trait_scores: dict[str, float],
) -> dict[str, float]:
    dimensions = sorted(set(baseline_trait_scores) | set(comparison_trait_scores))
    diffs = {
        name: round(abs(comparison_trait_scores.get(name, 0.0) - baseline_trait_scores.get(name, 0.0)), 4)
        for name in dimensions
    }
    if not diffs:
        return {"index": 0.0}
    index = round(sum(diffs.values()) / len(diffs), 4)
    diffs["index"] = index
    return diffs
