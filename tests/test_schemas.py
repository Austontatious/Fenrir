from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from fenrir.batteries.registry import get_battery
from fenrir.storage.models import ConditionProvenance, ReportRecord, WrapperDependenceReport, artifact_json_schemas


def test_report_schema_accepts_internal_report_shape() -> None:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "schemas" / "report.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    report = ReportRecord(
        run_id="r1",
        summary="ok",
        trait_scores={"clarity": 0.5},
        risk_flags={"overconfident_language_count": 0, "error_state_count": 0},
        stability_metrics={
            "mean_latency_ms": 10.0,
            "non_error_rate": 1.0,
            "response_uniqueness": 1.0,
            "fragility_rate": 0.0,
        },
        wrapper_dependence=WrapperDependenceReport(
            index=0.0,
            bucket="low",
            explanation="No pair coverage.",
            pair_deltas={},
        ),
        contradictions=[],
        coverage={"items_executed": 1},
        condition_provenance=ConditionProvenance(
            condition_id="eval_control",
            condition_version="1.0.0",
            system_prompt_source="prompts/system/fenrir_eval_control.md",
            system_prompt_hash="abc123",
            prompt_template_version="eval_control.prompt.v1",
        ),
        caveats=["stub"],
        prohibited_inferences=["no diagnosis"],
    )
    jsonschema.validate(report.model_dump(), schema)


def test_artifact_schema_export_matches_committed_report_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    committed = json.loads((root / "schemas" / "report.schema.json").read_text(encoding="utf-8"))
    exported = artifact_json_schemas()["report"]
    assert committed == exported


def test_battery_items_include_required_fields() -> None:
    root = Path(__file__).resolve().parents[1] / "batteries"
    battery = get_battery(root, "frontier_alignment_v1")
    first = battery.items[0]
    assert first.item_id
    assert first.prompt
    assert first.response_schema_ref
