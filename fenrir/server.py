from __future__ import annotations

import argparse
import json
import sys

from fenrir.config import FenrirConfig
from fenrir.local_runtime import resolve_service_port
from fenrir.local_service import serve_local_service
from fenrir.logging import configure_logging
from fenrir.mcp.tools import FenrirMCPTools


LEGACY_TOOL_CHOICES = {"list_batteries", "describe_battery", "list_conditions"}


def _build_parser(config: FenrirConfig) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fenrir server entrypoint")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tool_parser = subparsers.add_parser("tool", help="Run MCP-style tool facade command")
    tool_parser.add_argument("tool", choices=sorted(LEGACY_TOOL_CHOICES))
    tool_parser.add_argument("--battery-id", default="frontier_alignment_v1")

    local_parser = subparsers.add_parser("serve-local", help="Start setup-first local Fenrir service")
    local_parser.add_argument("--host", default=config.service_host)
    local_parser.add_argument("--port", type=int, default=config.service_port)
    local_parser.add_argument("--port-scan-limit", type=int, default=config.service_port_scan_limit)
    local_parser.add_argument("--strict-port", action="store_true")

    return parser


def _normalize_legacy_argv(argv: list[str] | None) -> list[str] | None:
    if not argv:
        return argv
    if argv[0] in LEGACY_TOOL_CHOICES:
        return ["tool", *argv]
    return argv


def _run_tool(*, config: FenrirConfig, tool_name: str, battery_id: str) -> int:
    tools = FenrirMCPTools(
        battery_root=config.battery_root,
        run_output_root=config.run_output_root,
    )

    if tool_name == "list_batteries":
        payload = tools.list_batteries()
    elif tool_name == "describe_battery":
        payload = tools.describe_battery(battery_id)
    else:
        payload = tools.list_conditions()

    print(json.dumps(payload, indent=2))
    return 0


def _run_local_service(*, config: FenrirConfig, host: str, port: int, strict_port: bool, scan_limit: int) -> int:
    resolved = resolve_service_port(host, port, scan_limit=1 if strict_port else max(1, scan_limit))
    if resolved != port:
        print(f"[fenrir-server] requested port {port} unavailable; using {resolved}")

    serve_local_service(host=host, port=resolved, state_path=config.local_config_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    config = FenrirConfig.from_env()
    parser = _build_parser(config)
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    normalized = _normalize_legacy_argv(raw_argv)
    args = parser.parse_args(normalized)

    if args.command == "tool":
        return _run_tool(config=config, tool_name=args.tool, battery_id=args.battery_id)

    if args.command == "serve-local":
        return _run_local_service(
            config=config,
            host=args.host,
            port=args.port,
            strict_port=args.strict_port,
            scan_limit=args.port_scan_limit,
        )

    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
