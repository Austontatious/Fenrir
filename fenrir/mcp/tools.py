from __future__ import annotations

import json
from pathlib import Path

from fenrir.adapters.base import MockAdapter
from fenrir.batteries.registry import get_battery, list_batteries
from fenrir.conditions.registry import list_conditions
from fenrir.mcp.schemas import CompareRunsRequest, GenerateReportRequest, RunBatteryRequest
from fenrir.orchestrator.runner import BatteryRunner
from fenrir.scoring.wrapper_dependence import compute_wrapper_dependence
from fenrir.storage.run_store import RunStore


class FenrirMCPTools:
    """MCP tool-shaped facade used by a future wire-level server implementation."""

    def __init__(self, *, battery_root: Path, run_output_root: Path) -> None:
        self._battery_root = battery_root
        self._runner = BatteryRunner(battery_root=battery_root, store=RunStore(run_output_root))

    def list_batteries(self) -> dict[str, object]:
        return {
            "batteries": [
                {
                    "battery_id": descriptor.id,
                    "version": descriptor.version,
                    "description": descriptor.description,
                }
                for descriptor in list_batteries(self._battery_root)
            ]
        }

    def describe_battery(self, battery_id: str) -> dict[str, object]:
        battery = get_battery(self._battery_root, battery_id)
        return {
            "metadata": battery.spec.metadata.model_dump(),
            "dimensions": battery.spec.dimensions,
            "item_count": len(battery.items),
            "condition_compatibility": battery.spec.condition_compatibility,
            "stopping_policy_defaults": battery.spec.stopping_policy_defaults,
        }

    def list_conditions(self) -> dict[str, object]:
        return {
            "conditions": [
                {
                    "condition_id": condition.id,
                    "description": condition.description,
                    "apply_stressors": condition.apply_stressors,
                }
                for condition in list_conditions()
            ]
        }

    def run_battery(self, payload: dict[str, object]) -> dict[str, object]:
        request = RunBatteryRequest.model_validate(payload)
        artifacts = self._runner.run(
            battery_id=request.battery_id,
            condition_id=request.condition_id,
            model_target=request.model_target,
            adapter=MockAdapter(),
            sampling=request.sampling,
            stopping=request.stopping,
        )
        return {
            "run_id": artifacts.manifest.run_id,
            "output_dir": str(artifacts.output_dir),
            "summary": artifacts.report.summary,
        }

    def run_stability_sweep(self, payload: dict[str, object]) -> dict[str, object]:
        request = RunBatteryRequest.model_validate(payload)
        variants: list[dict[str, object]] = []
        for seed in (101, 202, 303):
            seeded = request.model_copy(update={"sampling": request.sampling.model_copy(update={"seed": seed})})
            result = self.run_battery(seeded.model_dump())
            variants.append(result)
        return {"runs": variants}

    def compare_runs(self, payload: dict[str, object]) -> dict[str, object]:
        request = CompareRunsRequest.model_validate(payload)
        baseline_report = self._load_report(request.baseline_run_id)
        candidate_report = self._load_report(request.candidate_run_id)
        return {
            "baseline_run_id": request.baseline_run_id,
            "candidate_run_id": request.candidate_run_id,
            "wrapper_dependence": compute_wrapper_dependence(
                baseline_report.get("trait_scores", {}),
                candidate_report.get("trait_scores", {}),
            ),
        }

    def generate_report(self, payload: dict[str, object]) -> dict[str, object]:
        request = GenerateReportRequest.model_validate(payload)
        run_dir = self._runner.run_root / request.run_id
        if request.format.lower() == "json":
            target = run_dir / "report.json"
            return {"run_id": request.run_id, "format": "json", "content": json.loads(target.read_text(encoding="utf-8"))}
        target = run_dir / "report.md"
        return {"run_id": request.run_id, "format": "markdown", "content": target.read_text(encoding="utf-8")}

    def _load_report(self, run_id: str) -> dict[str, object]:
        path = self._runner.run_root / run_id / "report.json"
        return json.loads(path.read_text(encoding="utf-8"))
