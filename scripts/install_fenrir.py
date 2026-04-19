#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fenrir.config import FenrirConfig
from fenrir.local_runtime import (
    build_service_url,
    default_local_state,
    load_local_state,
    resolve_service_port,
    save_local_state,
)


def parse_args(config: FenrirConfig, argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install and initialize Fenrir local setup")
    parser.add_argument("--skip-install", action="store_true", help="Skip pip install -e .[dev]")
    parser.add_argument("--host", default=config.service_host)
    parser.add_argument("--port", type=int, default=config.service_port)
    parser.add_argument("--port-scan-limit", type=int, default=config.service_port_scan_limit)
    parser.add_argument("--start", action="store_true", help="Start Fenrir service after setup")
    parser.add_argument("--strict-port", action="store_true", help="Fail if requested port is occupied")
    parser.add_argument(
        "--overwrite-state",
        action="store_true",
        help="Reset local state file to defaults before writing host/port.",
    )
    return parser.parse_args(argv)


def _run_install() -> None:
    cmd = [sys.executable, "-m", "pip", "install", "-e", ".[dev]"]
    print(f"[fenrir-install] running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(REPO_ROOT), check=True)


def _ensure_env_file() -> Path:
    env_path = REPO_ROOT / ".env"
    example = REPO_ROOT / ".env.example"
    if env_path.exists():
        print(f"[fenrir-install] existing env file kept: {env_path}")
        return env_path
    if not example.exists():
        raise RuntimeError(".env.example is missing")
    shutil.copyfile(example, env_path)
    print(f"[fenrir-install] created env file from template: {env_path}")
    return env_path


def _persist_state(
    config: FenrirConfig,
    *,
    host: str,
    port: int,
    overwrite_state: bool,
    state_path: Path | None = None,
) -> None:
    target_path = state_path or config.local_config_path
    if overwrite_state:
        state = default_local_state(config)
        init_mode = "reset"
    else:
        state = load_local_state(target_path, defaults=default_local_state(config))
        init_mode = "preserved"

    state.service_host = host
    state.service_port = port
    save_local_state(target_path, state)
    print(f"[fenrir-install] local config {init_mode}: {target_path}")


def main(argv: list[str] | None = None) -> int:
    config = FenrirConfig.from_env()
    args = parse_args(config, argv)

    if not args.skip_install:
        _run_install()
    else:
        print("[fenrir-install] skipping dependency installation by request")

    _ensure_env_file()

    scan_limit = 1 if args.strict_port else max(1, args.port_scan_limit)
    try:
        resolved_port = resolve_service_port(args.host, args.port, scan_limit=scan_limit)
    except RuntimeError as exc:
        print(f"[fenrir-install] error: {exc}")
        print(
            "[fenrir-install] choose another --port or increase --port-scan-limit; "
            "use --strict-port only when you require an exact port."
        )
        return 2
    if resolved_port != args.port:
        print(f"[fenrir-install] requested port {args.port} unavailable; using {resolved_port}")

    _persist_state(
        config,
        host=args.host,
        port=resolved_port,
        overwrite_state=bool(args.overwrite_state),
    )
    url = build_service_url(args.host, resolved_port)
    print(f"[fenrir-install] service URL: {url}")

    if args.start:
        start_cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "start_fenrir.py"),
            "--host",
            args.host,
            "--port",
            str(resolved_port),
        ]
        if args.strict_port:
            start_cmd.append("--strict-port")
        print(f"[fenrir-install] starting service: {' '.join(start_cmd)}")
        os.execv(sys.executable, start_cmd)

    print("[fenrir-install] setup complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
