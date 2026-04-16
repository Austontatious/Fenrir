from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fenrir.adapters.base import MockAdapter
from fenrir.config import FenrirConfig
from fenrir.orchestrator.runner import BatteryRunner
from fenrir.orchestrator.sampling import SamplingConfig
from fenrir.orchestrator.stopping import StoppingPolicy
from fenrir.storage.run_store import RunStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Fenrir smoke battery with the mock adapter")
    parser.add_argument("--battery-id", default="frontier_alignment_v1")
    parser.add_argument("--condition", default="eval_control")
    args = parser.parse_args(argv)

    config = FenrirConfig.from_env()
    runner = BatteryRunner(
        battery_root=config.battery_root,
        store=RunStore(config.run_output_root),
    )
    artifacts = runner.run(
        battery_id=args.battery_id,
        condition_id=args.condition,
        model_target="mock://local",
        adapter=MockAdapter(),
        sampling=SamplingConfig(),
        stopping=StoppingPolicy(max_items=4),
    )

    print(f"run_id={artifacts.manifest.run_id}")
    print(f"output_dir={artifacts.output_dir}")
    print(f"report_json={artifacts.output_dir / 'report.json'}")
    print(f"report_md={artifacts.output_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
