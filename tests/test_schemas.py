from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from fenrir.batteries.registry import get_battery
from fenrir.storage.models import ReportRecord


def test_report_schema_accepts_internal_report_shape() -> None:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "batteries" / "frontier_alignment_v1" / "schemas" / "report.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    report = ReportRecord(
        run_id="r1",
        summary="ok",
        trait_scores={"clarity": 0.5},
        risk_flags={"overconfidence_language_count": 0},
        stability_metrics={"mean_latency_ms": 10.0},
        wrapper_dependence={"index": 0.0},
        contradictions=[],
        coverage={"items_executed": 1},
        caveats=["stub"],
        prohibited_inferences=["no diagnosis"],
    )
    jsonschema.validate(report.model_dump(), schema)


def test_battery_items_include_required_fields() -> None:
    root = Path(__file__).resolve().parents[1] / "batteries"
    battery = get_battery(root, "frontier_alignment_v1")
    first = battery.items[0]
    assert first.item_id
    assert first.prompt
    assert first.response_schema_ref
