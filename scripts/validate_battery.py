from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import jsonschema

from fenrir.batteries.loader import load_battery


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Fenrir battery structure")
    parser.add_argument("--battery-root", default="batteries/frontier_alignment_v1")
    args = parser.parse_args(argv)

    battery_root = Path(args.battery_root).resolve()
    loaded = load_battery(battery_root)

    schema_path = battery_root / "schemas" / "report.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    sample_report = {
        "run_id": "sample",
        "summary": "sample",
        "trait_scores": {"clarity": 0.5},
        "risk_flags": {"overconfidence_language_count": 0},
        "stability_metrics": {"mean_latency_ms": 1.0},
        "wrapper_dependence": {"index": 0.0},
        "contradictions": [],
        "coverage": {"items_executed": len(loaded.items)},
        "caveats": ["sample"],
        "prohibited_inferences": ["sample"],
    }
    jsonschema.validate(sample_report, schema)

    print(f"[ok] battery={loaded.spec.metadata.id} items={len(loaded.items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
