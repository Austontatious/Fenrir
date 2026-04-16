from __future__ import annotations

import argparse
import json

from fenrir.config import FenrirConfig
from fenrir.logging import configure_logging
from fenrir.mcp.tools import FenrirMCPTools


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fenrir MCP tool skeleton")
    parser.add_argument("tool", choices=["list_batteries", "describe_battery", "list_conditions"]) 
    parser.add_argument("--battery-id", default="frontier_alignment_v1")
    args = parser.parse_args(argv)

    configure_logging()
    config = FenrirConfig.from_env()
    tools = FenrirMCPTools(
        battery_root=config.battery_root,
        run_output_root=config.run_output_root,
    )

    if args.tool == "list_batteries":
        payload = tools.list_batteries()
    elif args.tool == "describe_battery":
        payload = tools.describe_battery(args.battery_id)
    else:
        payload = tools.list_conditions()

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
