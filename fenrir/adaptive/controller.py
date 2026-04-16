from __future__ import annotations

from dataclasses import dataclass

from fenrir.adaptive.instantiator import next_level
from fenrir.adaptive.schemas import AdaptiveDecision, AdaptiveResponseFeatures, LadderLevelId


@dataclass(frozen=True)
class ControllerConfig:
    start_level: LadderLevelId = "L2"
    max_level: LadderLevelId = "L5"
    max_branch_probes_per_level: int = 1


@dataclass(frozen=True)
class ControllerState:
    current_level: LadderLevelId
    branch_count_at_level: int = 0
    shift_confirmed: bool = False


def initial_state(config: ControllerConfig = ControllerConfig()) -> ControllerState:
    return ControllerState(current_level=config.start_level, branch_count_at_level=0, shift_confirmed=False)


def decide_next_action(
    *,
    features: AdaptiveResponseFeatures,
    state: ControllerState,
    config: ControllerConfig = ControllerConfig(),
) -> AdaptiveDecision:
    at_max_level = state.current_level == config.max_level
    can_branch = state.branch_count_at_level < config.max_branch_probes_per_level

    if features.ambiguity:
        if can_branch:
            return AdaptiveDecision(next_action="branch_probe", reason="ambiguity", next_level=state.current_level)
        return AdaptiveDecision(next_action="stop", reason="ambiguity", next_level=None)

    if features.contradiction:
        if can_branch:
            return AdaptiveDecision(next_action="branch_probe", reason="contradiction", next_level=state.current_level)
        return AdaptiveDecision(next_action="stop", reason="contradiction", next_level=None)

    if features.shift_detected:
        if state.shift_confirmed or at_max_level:
            return AdaptiveDecision(next_action="stop", reason="threshold_crossed", next_level=None)
        if can_branch:
            return AdaptiveDecision(next_action="branch_probe", reason="threshold_crossed", next_level=state.current_level)
        return AdaptiveDecision(next_action="stop", reason="threshold_crossed", next_level=None)

    candidate = next_level(state.current_level)
    if candidate is None or at_max_level:
        return AdaptiveDecision(next_action="stop", reason="max_depth", next_level=None)

    return AdaptiveDecision(next_action="escalate", reason="stable_no_signal", next_level=candidate)
