from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class FenrirConfig:
    """Repository-local runtime configuration surface."""

    battery_root: Path
    run_output_root: Path
    default_condition: str
    default_temperature: float
    default_max_output_tokens: int
    openai_base_url: str
    openai_api_key: str
    openai_model: str

    @classmethod
    def from_env(cls, *, prefix: str = "FENRIR_") -> "FenrirConfig":
        return cls(
            battery_root=Path(os.getenv(f"{prefix}BATTERY_ROOT", "batteries")).resolve(),
            run_output_root=Path(os.getenv(f"{prefix}RUN_OUTPUT_ROOT", "artifacts/runs")).resolve(),
            default_condition=os.getenv(f"{prefix}DEFAULT_CONDITION", "eval_control").strip() or "eval_control",
            default_temperature=_env_float(f"{prefix}DEFAULT_TEMPERATURE", 0.2),
            default_max_output_tokens=_env_int(f"{prefix}DEFAULT_MAX_OUTPUT_TOKENS", 220),
            openai_base_url=os.getenv(f"{prefix}OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
            openai_api_key=os.getenv(
                f"{prefix}OPENAI_API_KEY",
                os.getenv("OPENAI_API_KEY", ""),
            ).strip(),
            openai_model=os.getenv(f"{prefix}OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
        )
