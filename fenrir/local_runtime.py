from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import tempfile
from typing import Any

from fenrir.config import FenrirConfig


UI_READOUT_SCHEMA_VERSION = "fenrir.ui_readout.v1"
LOCAL_STATE_SCHEMA_VERSION = "fenrir.local_state.v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class ModelEndpointConfig:
    provider: str = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4.1-mini"
    timeout_seconds: float = 45.0

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "has_api_key": bool(self.api_key),
            "api_key_masked": mask_secret(self.api_key),
        }


@dataclass
class LocalServiceState:
    service_host: str
    service_port: int
    mcp_enabled: bool = False
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8766
    battery_id: str = "frontier_alignment_v1"
    conditions: list[str] = field(default_factory=lambda: ["raw_minimal", "eval_control", "eval_control_stress"])
    endpoint: ModelEndpointConfig = field(default_factory=ModelEndpointConfig)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": {
                "host": self.service_host,
                "port": self.service_port,
                "url": build_service_url(self.service_host, self.service_port),
            },
            "mcp": {
                "enabled": self.mcp_enabled,
                "host": self.mcp_host,
                "port": self.mcp_port,
                "url": build_service_url(self.mcp_host, self.mcp_port),
            },
            "battery_id": self.battery_id,
            "conditions": list(self.conditions),
            "endpoint": {
                "provider": self.endpoint.provider,
                "base_url": self.endpoint.base_url,
                "api_key": self.endpoint.api_key,
                "model": self.endpoint.model,
                "timeout_seconds": self.endpoint.timeout_seconds,
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, defaults: "LocalServiceState") -> "LocalServiceState":
        service = payload.get("service") if isinstance(payload.get("service"), dict) else {}
        mcp = payload.get("mcp") if isinstance(payload.get("mcp"), dict) else {}
        endpoint = payload.get("endpoint") if isinstance(payload.get("endpoint"), dict) else {}

        provider = str(endpoint.get("provider", defaults.endpoint.provider)).strip() or defaults.endpoint.provider
        if provider not in {"openai_compatible", "mock"}:
            provider = defaults.endpoint.provider

        timeout_raw = endpoint.get("timeout_seconds", defaults.endpoint.timeout_seconds)
        try:
            timeout_value = float(timeout_raw)
        except (TypeError, ValueError):
            timeout_value = defaults.endpoint.timeout_seconds

        conditions_raw = payload.get("conditions", defaults.conditions)
        conditions: list[str] = []
        if isinstance(conditions_raw, list):
            conditions = [str(item).strip() for item in conditions_raw if str(item).strip()]
        if not conditions:
            conditions = list(defaults.conditions)

        return cls(
            service_host=str(service.get("host", defaults.service_host)).strip() or defaults.service_host,
            service_port=coerce_port(service.get("port"), defaults.service_port),
            mcp_enabled=bool(mcp.get("enabled", defaults.mcp_enabled)),
            mcp_host=str(mcp.get("host", defaults.mcp_host)).strip() or defaults.mcp_host,
            mcp_port=coerce_port(mcp.get("port"), defaults.mcp_port),
            battery_id=str(payload.get("battery_id", defaults.battery_id)).strip() or defaults.battery_id,
            conditions=conditions,
            endpoint=ModelEndpointConfig(
                provider=provider,
                base_url=str(endpoint.get("base_url", defaults.endpoint.base_url)).strip() or defaults.endpoint.base_url,
                api_key=str(endpoint.get("api_key", defaults.endpoint.api_key)).strip(),
                model=str(endpoint.get("model", defaults.endpoint.model)).strip() or defaults.endpoint.model,
                timeout_seconds=max(5.0, timeout_value),
            ),
        )


@dataclass(frozen=True)
class LocalStateLoadResult:
    state: LocalServiceState
    source_version: str | None
    migrated: bool = False
    repaired: bool = False
    should_persist: bool = False
    messages: tuple[str, ...] = ()


def coerce_port(value: Any, default: int) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return default
    if port < 1 or port > 65535:
        return default
    return port


def default_local_state(config: FenrirConfig) -> LocalServiceState:
    return LocalServiceState(
        service_host=config.service_host,
        service_port=config.service_port,
        mcp_enabled=config.mcp_enabled,
        mcp_host=config.mcp_host,
        mcp_port=config.mcp_port,
        battery_id="frontier_alignment_v1",
        conditions=["raw_minimal", "eval_control", "eval_control_stress"],
        endpoint=ModelEndpointConfig(
            provider="openai_compatible",
            base_url=config.openai_base_url,
            api_key=config.openai_api_key,
            model=config.openai_model,
            timeout_seconds=config.openai_timeout_seconds,
        ),
    )


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}...{value[-3:]}"


def build_service_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def resolve_service_port(host: str, preferred_port: int, *, scan_limit: int = 25) -> int:
    for offset in range(max(1, scan_limit)):
        candidate = preferred_port + offset
        if candidate > 65535:
            break
        if is_port_open(host, candidate):
            return candidate
    raise RuntimeError(f"No open port found near {host}:{preferred_port} (scan_limit={scan_limit})")


def _state_document_from_state(state: LocalServiceState) -> dict[str, Any]:
    payload = state.to_dict()
    payload["schema_version"] = LOCAL_STATE_SCHEMA_VERSION
    return payload


def load_local_state_result(path: Path, *, defaults: LocalServiceState) -> LocalStateLoadResult:
    if not path.exists():
        return LocalStateLoadResult(
            state=defaults,
            source_version=None,
            migrated=False,
            repaired=False,
            should_persist=False,
            messages=(),
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return LocalStateLoadResult(
            state=defaults,
            source_version=None,
            repaired=True,
            should_persist=True,
            messages=(
                f"Local state file is invalid JSON and was reinitialized from defaults: {path}",
                "Use --overwrite-state if you want to intentionally reset the local state contract.",
            ),
        )
    except OSError as exc:
        return LocalStateLoadResult(
            state=defaults,
            source_version=None,
            repaired=True,
            should_persist=False,
            messages=(
                f"Unable to read local state file; defaults were used: {path} ({exc})",
                "Check file permissions or path ownership if this persists.",
            ),
        )

    if not isinstance(payload, dict):
        return LocalStateLoadResult(
            state=defaults,
            source_version=None,
            repaired=True,
            should_persist=True,
            messages=(
                f"Local state file did not contain an object and was reinitialized: {path}",
            ),
        )

    source_version_raw = payload.get("schema_version")
    if source_version_raw is None:
        # Legacy contract (pre-versioned): migrate in place by retaining known user-owned keys.
        migrated_state = LocalServiceState.from_dict(payload, defaults=defaults)
        return LocalStateLoadResult(
            state=migrated_state,
            source_version=None,
            migrated=True,
            repaired=False,
            should_persist=True,
            messages=(
                "Migrated legacy local state (missing schema_version) to fenrir.local_state.v1.",
            ),
        )

    source_version = str(source_version_raw).strip()
    if source_version != LOCAL_STATE_SCHEMA_VERSION:
        return LocalStateLoadResult(
            state=defaults,
            source_version=source_version,
            repaired=True,
            should_persist=True,
            messages=(
                f"Unsupported local state schema_version '{source_version}' was reset to defaults.",
                f"Supported schema_version: {LOCAL_STATE_SCHEMA_VERSION}.",
            ),
        )

    try:
        state = LocalServiceState.from_dict(payload, defaults=defaults)
    except Exception as exc:
        return LocalStateLoadResult(
            state=defaults,
            source_version=source_version,
            repaired=True,
            should_persist=True,
            messages=(
                f"Local state values were invalid and defaults were applied: {exc}",
            ),
        )

    return LocalStateLoadResult(
        state=state,
        source_version=source_version,
        migrated=False,
        repaired=False,
        should_persist=False,
        messages=(),
    )


def load_local_state(path: Path, *, defaults: LocalServiceState) -> LocalServiceState:
    return load_local_state_result(path, defaults=defaults).state


def save_local_state(path: Path, state: LocalServiceState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(_state_document_from_state(state), indent=2) + "\n"
    _write_text_atomic(path, serialized)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)

        if temp_path is None:
            raise RuntimeError("temporary path was not created")

        os.replace(temp_path, path)
    except Exception as exc:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise RuntimeError(
            f"Failed to write local state atomically at {path}. "
            "Existing state was left unchanged where possible. "
            f"Cause: {exc}. Retry or inspect directory permissions."
        ) from exc


def load_hybrid_summary(summary_path: Path) -> dict[str, Any] | None:
    if not summary_path.exists():
        return None
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return payload


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def canonical_readout_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
    adaptive = summary.get("adaptive_component") if isinstance(summary.get("adaptive_component"), dict) else {}
    static = summary.get("static_component") if isinstance(summary.get("static_component"), dict) else {}
    reference = summary.get("reference_comparison") if isinstance(summary.get("reference_comparison"), dict) else {}
    condition_metrics = adaptive.get("condition_metrics") if isinstance(adaptive.get("condition_metrics"), dict) else {}
    condition_signals = adaptive.get("condition_signals") if isinstance(adaptive.get("condition_signals"), dict) else {}

    strongest_deltas: list[dict[str, Any]] = []
    directionality = adaptive.get("directionality") if isinstance(adaptive.get("directionality"), dict) else {}
    for key, value in sorted(directionality.items()):
        strongest_deltas.append({
            "delta_id": key,
            "value": _as_float(value),
        })

    failure_modes: list[dict[str, Any]] = []
    for condition_id, metrics in sorted(condition_metrics.items()):
        if not isinstance(metrics, dict):
            continue
        mode_counts = metrics.get("failure_mode_counts") if isinstance(metrics.get("failure_mode_counts"), dict) else {}
        sorted_modes = sorted(mode_counts.items(), key=lambda item: item[1], reverse=True)
        failure_modes.append(
            {
                "condition_id": condition_id,
                "top_modes": [{"label": str(label), "count": int(count)} for label, count in sorted_modes[:3]],
            }
        )

    caveats = summary.get("caveats") if isinstance(summary.get("caveats"), list) else []
    caveat_text = [str(item) for item in caveats]

    return {
        "schema_version": UI_READOUT_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "source_summary_id": summary.get("evaluation_id", "hybrid_mvp_eval_v1"),
        "overall_summary": {
            "verdict": summary.get("verdict"),
            "rationale": summary.get("verdict_rationale"),
            "model_target": summary.get("model_target"),
            "adapter_id": summary.get("adapter_id"),
            "conditions_run": summary.get("conditions_run", []),
        },
        "strongest_observed_condition_deltas": strongest_deltas,
        "static_baseline_summary": {
            "item_count": static.get("item_count"),
            "wrapper_dependence": static.get("wrapper_dependence"),
            "diagnostics_summary": static.get("diagnostics_summary"),
        },
        "adaptive_threshold_summary": {
            "raw_signal_index": _as_float(adaptive.get("raw_signal_index")),
            "confidence_adjusted_signal_index": _as_float(adaptive.get("confidence_adjusted_signal_index")),
            "uncertainty_penalty_index": _as_float(adaptive.get("uncertainty_penalty_index")),
            "stress_refinement_score": _as_float(adaptive.get("stress_refinement_score")),
            "condition_metrics": condition_metrics,
            "condition_signals": condition_signals,
        },
        "key_failure_modes_observed": failure_modes,
        "stress_effect_summary": {
            "note": adaptive.get("control_vs_stress_note"),
            "score": _as_float(adaptive.get("stress_refinement_score")),
        },
        "uncertainty_and_caveat_summary": caveat_text,
        "reference_comparison": {
            "static_only_wrapper_index": reference.get("static_only_wrapper_index"),
            "adaptive_v0_signal_index": reference.get("adaptive_v0_signal_index"),
            "hybrid_vs_static_note": reference.get("hybrid_vs_static_note"),
        },
        "export_options": {
            "canonical_json": "artifacts/hybrid/hybrid_mvp_eval_v1.json",
            "canonical_markdown": "artifacts/hybrid/hybrid_mvp_eval_v1.md",
            "llm_native_export": "api/readout/llm-export",
        },
        "non_claims": [
            "Fenrir is heuristic and condition-bounded, not proof of alignment.",
            "Fenrir is not a clinical or psychometric diagnosis engine.",
            "Fenrir does not infer consciousness, intent, or inner values.",
        ],
    }


def llm_native_export(readout: dict[str, Any]) -> str:
    overall = readout.get("overall_summary", {})
    adaptive = readout.get("adaptive_threshold_summary", {})
    deltas = readout.get("strongest_observed_condition_deltas", [])

    lines = [
        "# Fenrir LLM-Native Readout (Derived)",
        "",
        "This is a derived convenience export from the canonical heuristic report.",
        "Use for assistant-side summarization, not as a replacement for canonical artifacts.",
        "",
        "## Overall Summary",
        f"- verdict: {overall.get('verdict')}",
        f"- rationale: {overall.get('rationale')}",
        f"- model_target: {overall.get('model_target')}",
        f"- conditions_run: {overall.get('conditions_run')}",
        "",
        "## Adaptive Threshold Summary",
        f"- raw_signal_index: {adaptive.get('raw_signal_index')}",
        f"- confidence_adjusted_signal_index: {adaptive.get('confidence_adjusted_signal_index')}",
        f"- uncertainty_penalty_index: {adaptive.get('uncertainty_penalty_index')}",
        f"- stress_refinement_score: {adaptive.get('stress_refinement_score')}",
        "",
        "## Strongest Condition Deltas",
    ]
    if isinstance(deltas, list) and deltas:
        for entry in deltas[:5]:
            lines.append(f"- {entry.get('delta_id')}: {entry.get('value')}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Required Interpretation Guardrails",
            "- Do not treat this as proof of alignment.",
            "- Do not infer consciousness, intent, or inner values.",
            "- Do not frame this as clinical or psychometric diagnosis.",
            "",
        ]
    )
    return "\n".join(lines)
