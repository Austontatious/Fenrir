from __future__ import annotations

from dataclasses import dataclass
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
from typing import Any

from fenrir.adapters.base import ChatMessage, ModelRequest
from fenrir.adapters.openai_compatible import OpenAICompatibleAdapter
from fenrir.batteries.registry import list_batteries
from fenrir.conditions.registry import list_conditions
from fenrir.config import FenrirConfig
from fenrir.local_runtime import (
    LocalServiceState,
    build_service_url,
    canonical_readout_from_summary,
    default_local_state,
    llm_native_export,
    load_hybrid_summary,
    load_local_state,
    mask_secret,
    save_local_state,
    utc_now_iso,
)


@dataclass
class FenrirLocalService:
    config: FenrirConfig
    state_path: Path

    def __post_init__(self) -> None:
        defaults = default_local_state(self.config)
        self.state = load_local_state(self.state_path, defaults=defaults)
        save_local_state(self.state_path, self.state)

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def summary_path(self) -> Path:
        return self.repo_root / "artifacts" / "hybrid" / "hybrid_mvp_eval_v1.json"

    def health_payload(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "fenrir_local_service",
            "timestamp": utc_now_iso(),
            "service_url": build_service_url(self.state.service_host, self.state.service_port),
        }

    def status_payload(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": {
                "host": self.state.service_host,
                "port": self.state.service_port,
                "url": build_service_url(self.state.service_host, self.state.service_port),
            },
            "model_endpoint": self.state.endpoint.to_public_dict(),
            "battery_id": self.state.battery_id,
            "conditions": list(self.state.conditions),
            "latest_summary_exists": self.summary_path.exists(),
            "mcp": self.mcp_info(),
        }

    def mcp_info(self) -> dict[str, Any]:
        return {
            "enabled": bool(self.state.mcp_enabled),
            "host": self.state.mcp_host,
            "port": self.state.mcp_port,
            "mode": "optional_cli_tool_surface",
            "usage": [
                "fenrir-server list_batteries",
                "fenrir-server describe_battery --battery-id frontier_alignment_v1",
                "fenrir-server list_conditions",
            ],
            "note": "MCP-style tooling is optional interoperability; direct endpoint setup is the primary path.",
        }

    def available_modes_payload(self) -> dict[str, Any]:
        batteries = list_batteries(self.config.battery_root)
        conditions = list_conditions()
        return {
            "batteries": [
                {
                    "battery_id": descriptor.id,
                    "version": descriptor.version,
                    "description": descriptor.description,
                }
                for descriptor in batteries
            ],
            "conditions": [
                {
                    "condition_id": condition.id,
                    "condition_version": condition.version,
                    "description": condition.description,
                }
                for condition in conditions
            ],
            "default_battery_id": self.state.battery_id,
            "default_conditions": list(self.state.conditions),
        }

    def config_payload(self) -> dict[str, Any]:
        endpoint = self.state.endpoint
        return {
            "provider": endpoint.provider,
            "base_url": endpoint.base_url,
            "model": endpoint.model,
            "timeout_seconds": endpoint.timeout_seconds,
            "battery_id": self.state.battery_id,
            "conditions": list(self.state.conditions),
            "has_api_key": bool(endpoint.api_key),
            "api_key_masked": mask_secret(endpoint.api_key),
            "mcp_enabled": self.state.mcp_enabled,
            "mcp_host": self.state.mcp_host,
            "mcp_port": self.state.mcp_port,
        }

    def update_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = self.state.endpoint

        provider = str(payload.get("provider", endpoint.provider)).strip() or endpoint.provider
        if provider not in {"openai_compatible", "mock"}:
            raise ValueError("provider must be one of: openai_compatible, mock")

        base_url = str(payload.get("base_url", endpoint.base_url)).strip() or endpoint.base_url
        model = str(payload.get("model", endpoint.model)).strip() or endpoint.model
        battery_id = str(payload.get("battery_id", self.state.battery_id)).strip() or self.state.battery_id

        timeout_raw = payload.get("timeout_seconds", endpoint.timeout_seconds)
        try:
            timeout_seconds = max(5.0, float(timeout_raw))
        except (TypeError, ValueError):
            timeout_seconds = endpoint.timeout_seconds

        incoming_conditions = payload.get("conditions")
        if isinstance(incoming_conditions, list):
            parsed_conditions = [str(item).strip() for item in incoming_conditions if str(item).strip()]
            conditions = parsed_conditions or list(self.state.conditions)
        else:
            conditions = list(self.state.conditions)

        api_key = endpoint.api_key
        if "api_key" in payload:
            api_key = str(payload.get("api_key") or "").strip()

        mcp_enabled = bool(payload.get("mcp_enabled", self.state.mcp_enabled))
        mcp_host = str(payload.get("mcp_host", self.state.mcp_host)).strip() or self.state.mcp_host
        mcp_port_raw = payload.get("mcp_port", self.state.mcp_port)
        try:
            mcp_port = int(mcp_port_raw)
        except (TypeError, ValueError):
            mcp_port = self.state.mcp_port
        if mcp_port < 1 or mcp_port > 65535:
            mcp_port = self.state.mcp_port

        self.state.endpoint.provider = provider
        self.state.endpoint.base_url = base_url
        self.state.endpoint.model = model
        self.state.endpoint.timeout_seconds = timeout_seconds
        self.state.endpoint.api_key = api_key
        self.state.battery_id = battery_id
        self.state.conditions = conditions
        self.state.mcp_enabled = mcp_enabled
        self.state.mcp_host = mcp_host
        self.state.mcp_port = mcp_port
        save_local_state(self.state_path, self.state)
        return self.config_payload()

    def test_connection(self) -> dict[str, Any]:
        endpoint = self.state.endpoint
        if endpoint.provider == "mock":
            return {
                "status": "ok",
                "provider": "mock",
                "message": "Mock provider is active; connection test is trivially healthy.",
            }

        adapter = OpenAICompatibleAdapter(
            base_url=endpoint.base_url,
            model=endpoint.model,
            api_key=endpoint.api_key,
            timeout_seconds=endpoint.timeout_seconds,
        )
        response = adapter.generate(
            ModelRequest(
                messages=[
                    ChatMessage(role="system", content="Reply briefly and truthfully."),
                    ChatMessage(role="user", content="Respond with: connection_ok"),
                ],
                temperature=0.0,
                max_output_tokens=12,
                seed=11,
                structured_output=None,
            )
        )
        if response.error_state:
            return {
                "status": "error",
                "provider": endpoint.provider,
                "message": response.error_state,
                "model": endpoint.model,
            }

        return {
            "status": "ok",
            "provider": endpoint.provider,
            "model": endpoint.model,
            "base_url": endpoint.base_url,
            "sample_response": response.raw_response,
        }

    def run_evaluation(self) -> dict[str, Any]:
        endpoint = self.state.endpoint
        command = [
            sys.executable,
            str(self.repo_root / "scripts" / "run_hybrid_mvp_eval.py"),
        ]

        for condition in self.state.conditions:
            command.extend(["--condition", condition])

        if endpoint.provider == "mock":
            command.extend(["--adapter", "mock"])
        else:
            if not endpoint.api_key:
                raise RuntimeError("API key is required for openai_compatible provider")
            command.extend(
                [
                    "--adapter",
                    "openai",
                    "--openai-base-url",
                    endpoint.base_url,
                    "--openai-model",
                    endpoint.model,
                    "--openai-timeout-seconds",
                    str(endpoint.timeout_seconds),
                    "--openai-api-key",
                    endpoint.api_key,
                ]
            )

        proc = subprocess.run(
            command,
            cwd=str(self.repo_root),
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "unknown error").strip()
            raise RuntimeError(f"Hybrid evaluation failed: {detail}")

        summary = load_hybrid_summary(self.summary_path)
        if summary is None:
            raise RuntimeError("Evaluation completed but no summary was produced at artifacts/hybrid/hybrid_mvp_eval_v1.json")
        readout = canonical_readout_from_summary(summary)
        return {
            "status": "ok",
            "summary_path": str(self.summary_path),
            "canonical_readout": readout,
        }

    def latest_readout_payload(self) -> dict[str, Any]:
        summary = load_hybrid_summary(self.summary_path)
        if summary is None:
            return {
                "status": "missing",
                "message": "No hybrid summary found yet. Run an evaluation first.",
                "summary_path": str(self.summary_path),
            }
        return {
            "status": "ok",
            "summary_path": str(self.summary_path),
            "canonical_readout": canonical_readout_from_summary(summary),
        }

    def llm_export_payload(self) -> dict[str, Any]:
        latest = self.latest_readout_payload()
        if latest.get("status") != "ok":
            return latest
        readout = latest["canonical_readout"]
        return {
            "status": "ok",
            "format": "markdown",
            "content": llm_native_export(readout),
        }

    def frontend_html(self) -> str:
        template_path = Path(__file__).resolve().parent / "frontend" / "index.html"
        return template_path.read_text(encoding="utf-8")


class FenrirRequestHandler(BaseHTTPRequestHandler):
    server: "FenrirHTTPServer"

    def do_GET(self) -> None:  # noqa: N802
        app = self.server.app
        if self.path == "/":
            html = app.frontend_html().encode("utf-8")
            self._send_bytes(HTTPStatus.OK, html, "text/html; charset=utf-8")
            return
        if self.path == "/healthz":
            self._send_json(HTTPStatus.OK, app.health_payload())
            return
        if self.path == "/api/status":
            self._send_json(HTTPStatus.OK, app.status_payload())
            return
        if self.path == "/api/config":
            self._send_json(HTTPStatus.OK, app.config_payload())
            return
        if self.path == "/api/modes":
            self._send_json(HTTPStatus.OK, app.available_modes_payload())
            return
        if self.path == "/api/readout/latest":
            self._send_json(HTTPStatus.OK, app.latest_readout_payload())
            return
        if self.path == "/api/readout/llm-export":
            self._send_json(HTTPStatus.OK, app.llm_export_payload())
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"status": "error", "message": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        payload = self._read_json()
        app = self.server.app
        try:
            if self.path == "/api/config":
                updated = app.update_config(payload)
                self._send_json(HTTPStatus.OK, {"status": "ok", "config": updated})
                return
            if self.path == "/api/test-connection":
                self._send_json(HTTPStatus.OK, app.test_connection())
                return
            if self.path == "/api/run-evaluation":
                self._send_json(HTTPStatus.OK, app.run_evaluation())
                return
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"status": "error", "message": str(exc)})
            return
        except RuntimeError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"status": "error", "message": str(exc)})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"status": "error", "message": "not found"})

    def log_message(self, format: str, *args: Any) -> None:
        timestamp = utc_now_iso()
        message = format % args
        print(f"[{timestamp}] fenrir-local {self.client_address[0]} {message}")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        if not raw.strip():
            return {}
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object")
        return payload

    def _send_json(self, code: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self._send_bytes(code, body, "application/json")

    def _send_bytes(self, code: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(int(code))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class FenrirHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], app: FenrirLocalService) -> None:
        self.app = app
        super().__init__(server_address, FenrirRequestHandler)


def serve_local_service(*, host: str, port: int, state_path: Path | None = None) -> None:
    config = FenrirConfig.from_env()
    app = FenrirLocalService(config=config, state_path=state_path or config.local_config_path)
    app.state.service_host = host
    app.state.service_port = port
    save_local_state(app.state_path, app.state)

    server = FenrirHTTPServer((host, port), app)
    base_url = build_service_url(host, port)
    print(f"[fenrir-local] service listening on {base_url}")
    print(f"[fenrir-local] setup UI: {base_url}/")
    print(f"[fenrir-local] health endpoint: {base_url}/healthz")
    print(
        "[fenrir-local] mcp optional mode: "
        + ("enabled" if app.state.mcp_enabled else "disabled")
        + f" (host={app.state.mcp_host} port={app.state.mcp_port})"
    )
    server.serve_forever()
