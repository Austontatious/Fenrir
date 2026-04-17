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


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
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
    openai_timeout_seconds: float
    service_host: str
    service_port: int
    service_port_scan_limit: int
    local_state_dir: Path
    local_config_path: Path
    mcp_enabled: bool
    mcp_host: str
    mcp_port: int

    @classmethod
    def from_env(cls, *, prefix: str = "FENRIR_") -> "FenrirConfig":
        local_state_dir = Path(os.getenv(f"{prefix}LOCAL_STATE_DIR", ".fenrir")).resolve()
        local_config_default = local_state_dir / "local_config.json"
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
            openai_timeout_seconds=_env_float(f"{prefix}OPENAI_TIMEOUT_SECONDS", 45.0),
            service_host=os.getenv(f"{prefix}SERVICE_HOST", "127.0.0.1").strip() or "127.0.0.1",
            service_port=_env_int(f"{prefix}SERVICE_PORT", 8765),
            service_port_scan_limit=max(1, _env_int(f"{prefix}SERVICE_PORT_SCAN_LIMIT", 25)),
            local_state_dir=local_state_dir,
            local_config_path=Path(os.getenv(f"{prefix}LOCAL_CONFIG_PATH", str(local_config_default))).resolve(),
            mcp_enabled=_env_bool(f"{prefix}MCP_ENABLED", False),
            mcp_host=os.getenv(f"{prefix}MCP_HOST", "127.0.0.1").strip() or "127.0.0.1",
            mcp_port=_env_int(f"{prefix}MCP_PORT", 8766),
        )
