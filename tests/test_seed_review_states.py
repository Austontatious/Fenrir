from __future__ import annotations

from fenrir.generation.review_states import (
    REVIEW_STATES,
    is_valid_state,
    is_valid_transition,
    required_criteria_for_state,
    validate_transition,
)


def test_review_states_include_rewrite_requested() -> None:
    assert "rewrite_requested" in REVIEW_STATES
    assert is_valid_state("curated")
    assert not is_valid_state("archived")


def test_transition_rules_cover_primary_path() -> None:
    assert is_valid_transition("draft", "reviewed")
    assert is_valid_transition("reviewed", "curated")
    assert is_valid_transition("curated", "promoted")
    assert not is_valid_transition("draft", "promoted")


def test_validate_transition_reports_invalid_hops() -> None:
    ok = validate_transition("draft", "reviewed")
    bad = validate_transition("reviewed", "draft")
    assert ok.ok is True
    assert bad.ok is False
    assert "invalid transition" in bad.message


def test_required_criteria_documented_for_reviewed_curated_promoted() -> None:
    assert "schema_valid" in required_criteria_for_state("reviewed")
    assert "balanced_options" in required_criteria_for_state("curated")
    assert "controlled_run_executed" in required_criteria_for_state("promoted")
