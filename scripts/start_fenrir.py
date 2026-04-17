#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fenrir.config import FenrirConfig
from fenrir.local_runtime import build_service_url, resolve_service_port
from fenrir.local_service import serve_local_service


def parse_args(config: FenrirConfig, argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start Fenrir local setup-first service")
    parser.add_argument("--host", default=config.service_host)
    parser.add_argument("--port", type=int, default=config.service_port)
    parser.add_argument(
        "--port-scan-limit",
        type=int,
        default=config.service_port_scan_limit,
        help="Number of ports to scan upward when requested port is occupied.",
    )
    parser.add_argument("--strict-port", action="store_true", help="Fail instead of scanning for an open port.")
    parser.add_argument(
        "--state-path",
        type=Path,
        default=config.local_config_path,
        help="Local service state/config path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    config = FenrirConfig.from_env()
    args = parse_args(config, argv)

    requested_port = int(args.port)
    if requested_port < 1 or requested_port > 65535:
        raise SystemExit("--port must be between 1 and 65535")

    if args.strict_port:
        resolved_port = resolve_service_port(args.host, requested_port, scan_limit=1)
    else:
        resolved_port = resolve_service_port(args.host, requested_port, scan_limit=max(1, args.port_scan_limit))

    if resolved_port != requested_port:
        print(f"[fenrir-start] requested port {requested_port} unavailable; using {resolved_port}")

    url = build_service_url(args.host, resolved_port)
    print(f"[fenrir-start] starting Fenrir local service at {url}")
    serve_local_service(host=args.host, port=resolved_port, state_path=args.state_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
