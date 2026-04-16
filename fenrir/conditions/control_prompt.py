from __future__ import annotations

from pathlib import Path


PROMPTS_ROOT = Path(__file__).resolve().parents[2] / "prompts" / "system"


def prompt_path(name: str) -> Path:
    return PROMPTS_ROOT / f"{name}.md"


def load_prompt_template(name: str) -> str:
    return prompt_path(name).read_text(encoding="utf-8").strip()


def eval_control_prompt() -> str:
    return load_prompt_template("fenrir_eval_control")


def raw_minimal_prompt() -> str:
    return load_prompt_template("fenrir_raw_minimal")


def eval_control_stress_prompt() -> str:
    return load_prompt_template("fenrir_eval_control_stress")


def production_wrapper_prompt(default_text: str | None = None) -> str:
    if default_text and default_text.strip():
        return default_text.strip()
    return load_prompt_template("fenrir_production_wrapper_placeholder")
