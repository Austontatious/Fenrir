from __future__ import annotations

import random
from typing import Any
from uuid import uuid4

from fenrir.adaptive.schemas import AdaptiveProbeInstance, AdaptiveTemplateFamily, LadderLevelId, utc_now_iso


LEVEL_ORDER = ["L1", "L2", "L3", "L4", "L5"]


def _pick_slots(
    *,
    template: AdaptiveTemplateFamily,
    level_id: LadderLevelId,
    seed: int,
) -> dict[str, str]:
    randomizer = random.Random(f"{template.template_id}:{template.template_version}:{level_id}:{seed}")
    selected: dict[str, str] = {}
    for slot_id, choices in template.slots.items():
        selected[slot_id] = randomizer.choice(choices)
    return selected


def _level_instruction(template: AdaptiveTemplateFamily, level_id: LadderLevelId) -> str:
    for level in template.ladder:
        if level.level_id == level_id:
            return level.pressure_instruction
    raise ValueError(f"Unknown level {level_id} for template {template.template_id}")


def instantiate_probe(
    *,
    template: AdaptiveTemplateFamily,
    level_id: LadderLevelId,
    seed: int,
    slots_override: dict[str, str] | None = None,
    step_kind: str = "primary",
) -> AdaptiveProbeInstance:
    slots = _pick_slots(template=template, level_id=level_id, seed=seed)
    if slots_override:
        slots.update(slots_override)

    scenario = template.base_prompt_template.format(**slots)
    instruction = _level_instruction(template, level_id)

    prompt_lines = [
        scenario,
        "",
        f"Pressure level {level_id}: {instruction}",
        "",
        "Option A:",
        template.options["A"],
        "",
        "Option B:",
        template.options["B"],
        "",
        "Respond with exactly two lines:",
        "1) option_key: A or B",
        "2) rationale: one concise sentence",
    ]
    if step_kind == "branch_probe":
        prompt_lines.append("This is a consistency follow-up. Keep the same response format.")

    prompt_text = "\n".join(prompt_lines).strip()

    return AdaptiveProbeInstance(
        probe_id=uuid4().hex,
        template_id=template.template_id,
        template_version=template.template_version,
        family=template.family,
        dimension=template.dimension,
        ladder_level=level_id,
        slots=slots,
        prompt_text=prompt_text,
        stable_option=template.stable_option,
        pressure_option=template.pressure_option,
        provenance={
            "template_id": template.template_id,
            "template_version": template.template_version,
            "family": template.family,
            "dimension": template.dimension,
            "ladder_level": level_id,
            "seed": seed,
            "slots": slots,
            "instantiated_at": utc_now_iso(),
        },
    )


def make_branch_probe_prompt(
    *,
    template: AdaptiveTemplateFamily,
    level_id: LadderLevelId,
    previous_option: str,
) -> str:
    return template.branch_probe_template.format(
        previous_option=previous_option,
        ladder_level=level_id,
    ).strip()


def next_level(level_id: LadderLevelId) -> LadderLevelId | None:
    idx = LEVEL_ORDER.index(level_id)
    if idx + 1 >= len(LEVEL_ORDER):
        return None
    return LEVEL_ORDER[idx + 1]
