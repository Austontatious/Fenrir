from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fenrir.adapters.base import MockAdapter
from fenrir.orchestrator.runner import BatteryRunner
from fenrir.orchestrator.sampling import SamplingConfig
from fenrir.orchestrator.stopping import StoppingPolicy
from fenrir.storage.run_store import RunStore


CASES_ROOT = REPO_ROOT / "evals" / "cases"
DATASETS_ROOT = REPO_ROOT / "evals" / "datasets"


def run_check() -> int:
    errors: list[str] = []
    if not DATASETS_ROOT.is_dir():
        errors.append("missing evals/datasets")
    if not CASES_ROOT.is_dir():
        errors.append("missing evals/cases")
    case_files = sorted(CASES_ROOT.rglob("*.json"))
    if not case_files:
        errors.append("missing deterministic eval cases (*.json)")
    for path in case_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for key in ("name", "input", "expected"):
            if key not in payload:
                errors.append(f"{path.relative_to(REPO_ROOT)} missing key: {key}")

    if errors:
        for error in errors:
            print(f"[fail] {error}")
        return 1
    print(f"[ok] eval scaffolding present ({len(case_files)} case files)")
    return 0


def run_eval() -> int:
    runner = BatteryRunner(
        battery_root=REPO_ROOT / "batteries",
        store=RunStore(REPO_ROOT / "artifacts" / "evals"),
    )
    artifacts = runner.run(
        battery_id="frontier_alignment_v1",
        condition_id="eval_control",
        model_target="mock://local",
        adapter=MockAdapter(),
        sampling=SamplingConfig(),
        stopping=StoppingPolicy(max_items=3),
    )
    output = {
        "status": "pass",
        "run_id": artifacts.manifest.run_id,
        "output_dir": str(artifacts.output_dir),
    }
    target = REPO_ROOT / "evals" / "last_results.json"
    target.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"[ok] wrote eval results to {target.relative_to(REPO_ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fenrir eval runner")
    parser.add_argument("--check", action="store_true", help="validate only")
    args = parser.parse_args(argv)
    if args.check:
        return run_check()
    return run_eval()


if __name__ == "__main__":
    sys.exit(main())
