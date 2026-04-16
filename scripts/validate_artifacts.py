#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fenrir.storage.models import (
    ReportRecord,
    ResponseRecord,
    RunManifest,
    artifact_json_schemas,
    write_artifact_json_schemas,
)


SCHEMA_DIR = REPO_ROOT / "schemas"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_json(path: Path, schema: dict[str, object]) -> list[str]:
    validator = Draft202012Validator(schema)
    payload = _load_json(path)
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
    messages: list[str] = []
    for err in errors:
        label = ".".join(str(part) for part in err.path) or "<root>"
        messages.append(f"{path.name}::{label}: {err.message}")
    return messages


def _validate_run_directory(run_dir: Path, schemas: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    manifest_path = run_dir / "manifest.json"
    responses_path = run_dir / "responses.json"
    report_path = run_dir / "report.json"

    if not manifest_path.exists():
        errors.append(f"{run_dir}: missing manifest.json")
        return errors
    if not responses_path.exists():
        errors.append(f"{run_dir}: missing responses.json")
        return errors
    if not report_path.exists():
        errors.append(f"{run_dir}: missing report.json")
        return errors

    errors.extend(_validate_json(manifest_path, schemas["run_manifest"]))
    manifest_payload = _load_json(manifest_path)
    try:
        RunManifest.model_validate(manifest_payload)
    except Exception as exc:
        errors.append(f"manifest pydantic validation failed: {exc}")

    response_payload = _load_json(responses_path)
    if not isinstance(response_payload, list):
        errors.append(f"{responses_path.name} must contain an array")
    else:
        for idx, response in enumerate(response_payload):
            record_errors = sorted(
                Draft202012Validator(schemas["response_record"]).iter_errors(response),
                key=lambda err: list(err.path),
            )
            for err in record_errors:
                label = ".".join(str(part) for part in err.path) or "<root>"
                errors.append(f"responses.json[{idx}]::{label}: {err.message}")
            try:
                ResponseRecord.model_validate(response)
            except Exception as exc:
                errors.append(f"responses.json[{idx}] pydantic validation failed: {exc}")

    errors.extend(_validate_json(report_path, schemas["report"]))
    report_payload = _load_json(report_path)
    try:
        ReportRecord.model_validate(report_payload)
    except Exception as exc:
        errors.append(f"report pydantic validation failed: {exc}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Fenrir run artifacts against frozen contracts")
    parser.add_argument("--runs-root", type=Path, default=REPO_ROOT / "artifacts" / "runs")
    parser.add_argument("--run-id", default=None, help="Validate a single run id under --runs-root")
    parser.add_argument(
        "--write-schemas",
        action="store_true",
        help="Export current pydantic artifact schemas into ./schemas before validation",
    )
    args = parser.parse_args(argv)

    if args.write_schemas:
        written = write_artifact_json_schemas(SCHEMA_DIR)
        for name, path in written.items():
            print(f"[ok] wrote {name} schema to {path}")

    schemas = artifact_json_schemas()
    runs_root = args.runs_root

    if not runs_root.exists():
        print(f"[fail] runs root not found: {runs_root}")
        return 1

    if args.run_id:
        run_dirs = [runs_root / args.run_id]
    else:
        run_dirs = sorted(path for path in runs_root.iterdir() if path.is_dir())

    if not run_dirs:
        print("[fail] no run directories found")
        return 1

    failures: list[str] = []
    for run_dir in run_dirs:
        if not run_dir.exists():
            failures.append(f"missing run directory: {run_dir}")
            continue
        failures.extend(_validate_run_directory(run_dir, schemas))

    if failures:
        for line in failures:
            print(f"[fail] {line}")
        return 1

    print(f"[ok] validated {len(run_dirs)} run artifact directories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
