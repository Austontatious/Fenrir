from __future__ import annotations

from pathlib import Path

from fenrir.adapters.base import MockAdapter
from fenrir.orchestrator.runner import BatteryRunner
from fenrir.orchestrator.sampling import SamplingConfig
from fenrir.orchestrator.stopping import StoppingPolicy
from fenrir.storage.run_store import RunStore


def test_runner_smoke_creates_report_files(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    runner = BatteryRunner(
        battery_root=repo_root / "batteries",
        store=RunStore(tmp_path),
    )

    artifacts = runner.run(
        battery_id="frontier_alignment_v1",
        condition_id="eval_control",
        model_target="mock://test",
        adapter=MockAdapter(),
        sampling=SamplingConfig(),
        stopping=StoppingPolicy(max_items=3),
    )

    assert (artifacts.output_dir / "manifest.json").exists()
    assert (artifacts.output_dir / "responses.json").exists()
    assert (artifacts.output_dir / "report.json").exists()
    assert (artifacts.output_dir / "report.md").exists()
