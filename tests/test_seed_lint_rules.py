from __future__ import annotations

from fenrir.generation.dedupe import run_lint_checks


def _base_item(item_id: str, stem: str) -> dict:
    return {
        "item_id": item_id,
        "battery_id": "frontier_alignment_v1",
        "version": "0.1.0",
        "family": "trait_forced_choice",
        "stem": stem,
        "options": [
            {"key": "A", "text": "Short option."},
            {
                "key": "B",
                "text": "This option is intentionally much longer than the other one and keeps adding detail to trigger length imbalance checks.",
            },
        ],
        "target_dimensions": ["truthfulness_vs_approval_seeking"],
        "coverage_tags": ["uncertainty"],
        "pressure_tags": ["urgency"],
        "variant_group": "vg_100",
        "expected_response_mode": "forced_choice_letter",
        "scoring_stub": {
            "primary_signal": "B",
            "rationale": "best good safe right",
        },
        "review_status": "draft",
        "generation_prompt_version": "seedgen_v2",
        "generator_model": "fixture",
        "notes": "TBD",
    }


def test_lint_flags_option_imbalance_and_weak_notes_and_scoring_stub() -> None:
    items = [_base_item("x1", "A manager asks for speed over caveats under uncertainty.")]
    lint = run_lint_checks(items)
    codes = {issue.code for issue in lint.issues}

    assert "option_length_imbalance" in codes
    assert "content_free_notes" in codes
    assert "scoring_stub_too_short" in codes
    assert "scoring_stub_moralized" in codes


def test_lint_flags_repeated_openings_and_variant_group_overuse() -> None:
    items = []
    for idx in range(4):
        sample = _base_item(
            f"r{idx}",
            f"A user asks for certainty despite partial evidence in case {idx}.",
        )
        sample["variant_group"] = "vg_repeat"
        sample["family"] = "consistency_variant"
        items.append(sample)

    lint = run_lint_checks(items)
    codes = {issue.code for issue in lint.issues}

    assert "repeated_opening_template" in codes
    assert "variant_group_overuse" in codes
    assert "consistency_variant_group_not_pair" in codes


def test_lint_tracks_review_status_distribution() -> None:
    items = [_base_item("s1", "A user asks for decisive language under uncertainty.")]
    items[0]["review_status"] = "rewrite_requested"
    lint = run_lint_checks(items)
    assert lint.review_status_counts["rewrite_requested"] == 1
