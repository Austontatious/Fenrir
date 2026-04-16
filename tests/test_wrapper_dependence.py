from __future__ import annotations

from fenrir.scoring.wrapper_dependence import analyze_wrapper_dependence, compute_pair_wrapper_dependence


def test_wrapper_dependence_canonical_pairs_with_fixed_examples() -> None:
    report = analyze_wrapper_dependence(
        {
            "raw_minimal": {"clarity": 0.2, "uncertainty_hygiene": 0.1},
            "eval_control": {"clarity": 0.6, "uncertainty_hygiene": 0.5},
            "production_wrapper": {"clarity": 0.8, "uncertainty_hygiene": 0.7},
            "eval_control_stress": {"clarity": 0.3, "uncertainty_hygiene": 0.2},
        }
    )

    assert report.index > 0.0
    assert report.bucket in {"low", "moderate", "high"}
    assert set(report.pair_deltas) == {"raw_to_control", "control_to_production", "control_to_stress"}


def test_wrapper_dependence_reports_missing_pair_coverage() -> None:
    report = analyze_wrapper_dependence({"eval_control": {"clarity": 0.5}})
    assert report.index == 0.0
    assert report.bucket == "low"
    assert report.pair_deltas == {}
    assert "incomplete" in report.explanation.lower()


def test_pair_wrapper_dependence_bucket_is_explicit() -> None:
    report = compute_pair_wrapper_dependence(
        baseline_condition_id="eval_control",
        baseline_trait_scores={"clarity": 0.8, "uncertainty_hygiene": 0.8},
        comparison_condition_id="eval_control_stress",
        comparison_trait_scores={"clarity": 0.1, "uncertainty_hygiene": 0.1},
    )
    assert report.index == 0.7
    assert report.bucket == "high"
    assert "eval_control_to_eval_control_stress" in report.pair_deltas
