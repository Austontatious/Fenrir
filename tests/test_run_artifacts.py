from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from fenrir.adapters.base import MockAdapter
from fenrir.orchestrator.runner import BatteryRunner
from fenrir.orchestrator.sampling import SamplingConfig
from fenrir.orchestrator.stopping import StoppingPolicy
from fenrir.storage.models import RunManifest, artifact_json_schemas
from fenrir.storage.run_store import RunStore


def _run_sample(tmp_path: Path, condition_id: str = "eval_control"):
    repo_root = Path(__file__).resolve().parents[1]
    store = RunStore(tmp_path)
    runner = BatteryRunner(battery_root=repo_root / "batteries", store=store)
    return runner.run(
        battery_id="frontier_alignment_v1",
        condition_id=condition_id,
        model_target="mock://artifact-test",
        adapter=MockAdapter(),
        sampling=SamplingConfig(),
        stopping=StoppingPolicy(max_items=3),
        production_wrapper_text="Production safety wrapper for test." if condition_id == "production_wrapper" else None,
        production_wrapper_source="config://prod-wrapper-test" if condition_id == "production_wrapper" else None,
    )


def test_schema_roundtrip_and_serialization(tmp_path: Path) -> None:
    artifacts = _run_sample(tmp_path)
    schemas = artifact_json_schemas()

    manifest_path = artifacts.output_dir / "manifest.json"
    responses_path = artifacts.output_dir / "responses.json"
    report_path = artifacts.output_dir / "report.json"

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    responses_payload = json.loads(responses_path.read_text(encoding="utf-8"))
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert not list(Draft202012Validator(schemas["run_manifest"]).iter_errors(manifest_payload))
    assert not list(Draft202012Validator(schemas["report"]).iter_errors(report_payload))
    for response in responses_payload:
        assert not list(Draft202012Validator(schemas["response_record"]).iter_errors(response))

    roundtrip = RunManifest.model_validate_json(artifacts.manifest.model_dump_json())
    assert roundtrip == artifacts.manifest


def test_condition_provenance_population_and_scoring_trace(tmp_path: Path) -> None:
    artifacts = _run_sample(tmp_path, condition_id="production_wrapper")

    assert artifacts.report.condition_provenance.condition_id == "production_wrapper"
    assert artifacts.report.condition_provenance.production_wrapper_source == "config://prod-wrapper-test"
    assert artifacts.report.condition_provenance.system_prompt_hash

    for response in artifacts.responses:
        assert response.scoring_trace
        assert response.provenance.system_prompt_hash == artifacts.manifest.system_prompt_hash


def test_rejects_incomplete_run_manifest() -> None:
    with pytest.raises(ValidationError):
        RunManifest.model_validate(
            {
                "run_id": "x",
                "battery_id": "frontier_alignment_v1",
            }
        )
