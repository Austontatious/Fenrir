from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping


REVIEW_STATES = (
    "draft",
    "reviewed",
    "curated",
    "promoted",
    "rejected",
    "rewrite_requested",
)

TRANSITIONS: dict[str, set[str]] = {
    "draft": {"reviewed", "rejected", "rewrite_requested"},
    "reviewed": {"curated", "rejected", "rewrite_requested"},
    "curated": {"promoted", "rewrite_requested", "rejected"},
    "promoted": {"rewrite_requested", "rejected"},
    "rejected": set(),
    "rewrite_requested": {"reviewed", "rejected"},
}

STATE_CRITERIA: dict[str, list[str]] = {
    "reviewed": [
        "schema_valid",
        "metadata_complete",
        "dedupe_lint_checked",
        "human_reviewed",
    ],
    "curated": [
        "balanced_options",
        "non_obvious_tradeoff",
        "diagnostic_value_adequate",
        "non_redundant_against_curated",
    ],
    "promoted": [
        "controlled_run_executed",
        "scoring_behavior_acceptable",
        "no_major_ambiguity_detected",
    ],
}

REVIEW_ACTIONS = ("keep", "revise", "reject")

REASON_CODES = (
    "OBVIOUS_VIRTUE_SIGNAL",
    "OPTION_ASYMMETRY",
    "REPEATED_SKELETON",
    "BLAND_NON_DIAGNOSTIC",
    "MISSING_REALISTIC_PRESSURE",
    "METADATA_DRIFT",
    "SCORING_STUB_WEAK",
)


@dataclass(frozen=True)
class TransitionCheck:
    ok: bool
    message: str


def is_valid_state(state: str) -> bool:
    return state in REVIEW_STATES


def is_valid_transition(from_state: str, to_state: str) -> bool:
    if from_state == to_state:
        return True
    return to_state in TRANSITIONS.get(from_state, set())


def validate_transition(from_state: str, to_state: str) -> TransitionCheck:
    if not is_valid_state(from_state):
        return TransitionCheck(False, f"unknown source state '{from_state}'")
    if not is_valid_state(to_state):
        return TransitionCheck(False, f"unknown target state '{to_state}'")
    if is_valid_transition(from_state, to_state):
        return TransitionCheck(True, f"valid transition {from_state} -> {to_state}")
    return TransitionCheck(False, f"invalid transition {from_state} -> {to_state}")


def required_criteria_for_state(state: str) -> list[str]:
    return list(STATE_CRITERIA.get(state, []))


def summarize_state_counts(items: Iterable[Mapping[str, object]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        state = str(item.get("review_status", "")).strip() or "missing"
        counts[state] += 1
    return dict(counts)
