from __future__ import annotations

import json
from pathlib import Path

from fenrir.reports.markdown_report import render_markdown_report
from fenrir.storage.models import ReportRecord, ResponseRecord, RunManifest


class RunStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def save(self, *, manifest: RunManifest, responses: list[ResponseRecord], report: ReportRecord) -> Path:
        run_dir = self._root / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        (run_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        (run_dir / "responses.json").write_text(
            json.dumps([record.model_dump() for record in responses], indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (run_dir / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
        (run_dir / "report.md").write_text(render_markdown_report(report), encoding="utf-8")
        return run_dir

    def load_manifest(self, run_id: str) -> RunManifest:
        path = self._root / run_id / "manifest.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return RunManifest.model_validate(payload)

    def load_report(self, run_id: str) -> ReportRecord:
        path = self._root / run_id / "report.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ReportRecord.model_validate(payload)

    def load_responses(self, run_id: str) -> list[ResponseRecord]:
        path = self._root / run_id / "responses.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("responses.json must be an array")
        return [ResponseRecord.model_validate(item) for item in payload]
