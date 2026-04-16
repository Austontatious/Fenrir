from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Sequence

from core.prompt_loader import PromptLoader, PromptRender


PROMPT_VERSION = "seedgen_v1"
SYSTEM_PROMPT_NAME = "system/fenrir_seedgen_system_v1"

TASK_PROMPT_BY_FAMILY = {
    "trait_forced_choice": "tasks/fenrir_seedgen_trait_forced_choice_v1",
    "sjt_seed": "tasks/fenrir_seedgen_sjt_seed_v1",
    "redteam_behavioral_probe": "tasks/fenrir_seedgen_redteam_behavioral_probe_v1",
    "consistency_variant": "tasks/fenrir_seedgen_consistency_variant_v1",
}


@dataclass(frozen=True)
class PromptBundle:
    system_text: str
    user_text: str
    prompt_name: str
    prompt_sha256: str
    prompt_version: str


def _render_bullets(values: Sequence[str], *, fallback: str) -> str:
    cleaned = [value.strip() for value in values if value and value.strip()]
    if not cleaned:
        return f"- {fallback}"
    return "\n".join(f"- {value}" for value in cleaned)


def build_prompt_bundle(
    *,
    prompt_loader: PromptLoader,
    family: str,
    count: int,
    battery_id: str,
    version: str,
    generation_prompt_version: str,
    dimension_ids: Sequence[str],
    coverage_ids: Sequence[str],
    pressure_ids: Sequence[str],
    sensitivity_ids: Sequence[str],
) -> PromptBundle:
    if family not in TASK_PROMPT_BY_FAMILY:
        supported = ", ".join(sorted(TASK_PROMPT_BY_FAMILY))
        raise ValueError(f"Unsupported family '{family}'. Supported: {supported}")

    system_render = prompt_loader.render(SYSTEM_PROMPT_NAME)
    user_render = prompt_loader.render(
        TASK_PROMPT_BY_FAMILY[family],
        {
            "count": count,
            "battery_id": battery_id,
            "version": version,
            "generation_prompt_version": generation_prompt_version,
            "dimension_bullets": _render_bullets(
                dimension_ids,
                fallback="truthfulness_vs_approval_seeking",
            ),
            "coverage_bullets": _render_bullets(coverage_ids, fallback="uncertainty"),
            "pressure_bullets": _render_bullets(pressure_ids, fallback="user_pressure"),
            "sensitivity_bullets": _render_bullets(sensitivity_ids, fallback="moderate"),
        },
    )

    prompt_name = f"seedgen_{family}"
    prompt_sha256 = _joined_sha256(system_render, user_render)
    versions = [render.document.version for render in (system_render, user_render)]
    prompt_version = "+".join(version for version in versions if version != "unversioned")
    if not prompt_version:
        prompt_version = generation_prompt_version

    return PromptBundle(
        system_text=system_render.text,
        user_text=user_render.text,
        prompt_name=prompt_name,
        prompt_sha256=prompt_sha256,
        prompt_version=prompt_version,
    )


def _joined_sha256(system_render: PromptRender, user_render: PromptRender) -> str:
    joined = "\n".join(
        [
            system_render.document.sha256,
            user_render.document.sha256,
            system_render.input_hash,
            user_render.input_hash,
        ]
    )
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
