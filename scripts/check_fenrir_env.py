#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fenrir.config import FenrirConfig
from fenrir.local_runtime import (
    build_service_url,
    default_local_state,
    is_port_open,
    load_local_state_result,
    resolve_service_port,
)


REQUIRED_IMPORTS = (
    "pydantic",
    "yaml",
    "jsonschema",
)


def parse_args(config: FenrirConfig, argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Fenrir local environment readiness")
    parser.add_argument("--host", default=config.service_host)
    parser.add_argument("--port", type=int, default=config.service_port)
    parser.add_argument("--scan-limit", type=int, default=config.service_port_scan_limit)
    parser.add_argument(
        "--strict-port",
        action="store_true",
        help="Require the exact requested port to be free.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any check fails")
    return parser.parse_args(argv)


def _check_imports() -> tuple[bool, list[str]]:
    messages: list[str] = []
    all_ok = True
    for module_name in REQUIRED_IMPORTS:
        try:
            __import__(module_name)
            messages.append(f"[ok] import {module_name}")
        except Exception as exc:  # pragma: no cover - depends on environment
            all_ok = False
            messages.append(f"[fail] import {module_name}: {exc}")
    return all_ok, messages


def main(argv: list[str] | None = None) -> int:
    config = FenrirConfig.from_env()
    args = parse_args(config, argv)

    checks_ok = True
    print(f"[info] repo_root={REPO_ROOT}")

    if sys.version_info < (3, 11):
        checks_ok = False
        print("[fail] python >=3.11 is required")
    else:
        print(f"[ok] python {sys.version.split()[0]}")

    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        print(f"[ok] env file present: {env_path}")
    else:
        print(f"[warn] env file missing: {env_path} (copy from .env.example)")

    imports_ok, import_messages = _check_imports()
    checks_ok = checks_ok and imports_ok
    for line in import_messages:
        print(line)

    load_result = load_local_state_result(config.local_config_path, defaults=default_local_state(config))
    state = load_result.state
    print(f"[ok] local config path: {config.local_config_path}")
    print(f"[info] configured service url: {build_service_url(state.service_host, state.service_port)}")
    for message in load_result.messages:
        print(f"[warn] state notice: {message}")

    requested_port = int(args.port)
    if is_port_open(args.host, requested_port):
        print(f"[ok] requested port available: {args.host}:{requested_port}")
    else:
        if args.strict_port:
            checks_ok = False
            print(
                f"[fail] requested port occupied and --strict-port is set: "
                f"{args.host}:{requested_port}"
            )
        else:
            try:
                fallback = resolve_service_port(args.host, requested_port, scan_limit=max(1, args.scan_limit))
                print(
                    f"[warn] requested port occupied; fallback is runnable at "
                    f"{args.host}:{fallback}"
                )
            except RuntimeError as exc:
                checks_ok = False
                print(f"[fail] no free service port found: {exc}")

    if state.endpoint.provider == "openai_compatible" and not state.endpoint.api_key:
        print("[warn] local config has no API key; mock provider or API key required for live endpoint runs")

    if checks_ok:
        print("[ok] Fenrir local environment check completed")
        return 0

    if args.strict:
        return 1
    print("[warn] environment check completed with issues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
