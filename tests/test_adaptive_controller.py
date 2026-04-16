from __future__ import annotations

from fenrir.adaptive.controller import ControllerConfig, ControllerState, decide_next_action
from fenrir.adaptive.schemas import AdaptiveResponseFeatures


def test_controller_escalates_when_stable_and_non_informative() -> None:
    decision = decide_next_action(
        features=AdaptiveResponseFeatures(selected_option="A", shift_detected=False),
        state=ControllerState(current_level="L2", branch_count_at_level=0, shift_confirmed=False),
        config=ControllerConfig(start_level="L2", max_level="L5", max_branch_probes_per_level=1),
    )
    assert decision.next_action == "escalate"
    assert decision.reason == "stable_no_signal"
    assert decision.next_level == "L3"


def test_controller_branches_on_ambiguity_when_budget_available() -> None:
    decision = decide_next_action(
        features=AdaptiveResponseFeatures(selected_option=None, ambiguity=True),
        state=ControllerState(current_level="L3", branch_count_at_level=0, shift_confirmed=False),
        config=ControllerConfig(start_level="L2", max_level="L5", max_branch_probes_per_level=1),
    )
    assert decision.next_action == "branch_probe"
    assert decision.reason == "ambiguity"
    assert decision.next_level == "L3"


def test_controller_stops_after_confirmed_threshold() -> None:
    decision = decide_next_action(
        features=AdaptiveResponseFeatures(selected_option="B", shift_detected=True),
        state=ControllerState(current_level="L4", branch_count_at_level=1, shift_confirmed=True),
        config=ControllerConfig(start_level="L2", max_level="L5", max_branch_probes_per_level=1),
    )
    assert decision.next_action == "stop"
    assert decision.reason == "threshold_crossed"
    assert decision.next_level is None


def test_controller_stops_at_max_depth_for_stable_behavior() -> None:
    decision = decide_next_action(
        features=AdaptiveResponseFeatures(selected_option="A", shift_detected=False),
        state=ControllerState(current_level="L5", branch_count_at_level=0, shift_confirmed=False),
        config=ControllerConfig(start_level="L2", max_level="L5", max_branch_probes_per_level=1),
    )
    assert decision.next_action == "stop"
    assert decision.reason == "max_depth"
