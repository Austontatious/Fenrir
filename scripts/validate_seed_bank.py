#!/usr/bin/env python3
"""Validate Fenrir seed-bank files against schemas and lint rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fenrir.generation import (
    DEFAULT_BATTERY_ID,
    load_coverage_ids,
    load_dimension_ids,
    load_pressure_ids,
    load_seed_batch_schema,
    load_seed_item_schema,
)
from fenrir.generation.dedupe import run_lint_checks
from fenrir.generation.schemas import validate_batch, validate_item


DEFAULT_GENERATED_DIR = REPO_ROOT / "batteries" / DEFAULT_BATTERY_ID / "seeds" / "generated"
DEFAULT_METADATA_DIR = REPO_ROOT / "batteries" / DEFAULT_BATTERY_ID / "metadata"
DEFAULT_SCHEMA_DIR = REPO_ROOT / "batteries" / DEFAULT_BATTERY_ID / "schemas"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Fenrir seed bank artifacts")
    parser.add_argument("--input", type=Path, default=DEFAULT_GENERATED_DIR)
    parser.add_argument("--schema-dir", type=Path, default=DEFAULT_SCHEMA_DIR)
    parser.add_argument("--metadata-dir", type=Path, default=DEFAULT_METADATA_DIR)
    parser.add_argument("--report-json", type=Path, default=None)
    parser.add_argument("--fail-on-warnings", action="store_true")
    parser.add_argument("--near-duplicate-threshold", type=float, default=0.88)
    parser.add_argument("--pressure-concentration-threshold", type=float, default=0.55)
    return parser.parse_args()


def _discover_json_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    files = sorted(candidate for candidate in path.rglob("*.json") if candidate.is_file())
    return [candidate for candidate in files if "/raw/" not in candidate.as_posix()]


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_items(payload: Any) -> tuple[list[dict[str, Any]], list[str]]:
    issues: list[str] = []
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)], issues
        issues.append("JSON object missing items list")
        return [], issues
    if isinstance(payload, list):
        if all(isinstance(item, dict) for item in payload):
            return list(payload), issues
        issues.append("JSON list contains non-object items")
        return [], issues
    issues.append("JSON must be an object or list")
    return [], issues


def _print_counter(title: str, counter: dict[str, int], limit: int = 12) -> None:
    print(f"\n{title}:")
    if not counter:
        print("  (none)")
        return
    for key, count in sorted(counter.items(), key=lambda row: row[1], reverse=True)[:limit]:
        print(f"  - {key}: {count}")


def _render_schema_errors(path: Path, errors: Iterable[str]) -> list[dict[str, str]]:
    return [{"path": str(path), "error": error} for error in errors]


def main() -> None:
    args = parse_args()

    files = _discover_json_files(args.input)
    if not files:
        raise SystemExit(f"No JSON seed files found at {args.input}")

    batch_schema = load_seed_batch_schema(args.schema_dir)
    item_schema = load_seed_item_schema(args.schema_dir)

    known_dimensions = load_dimension_ids(args.metadata_dir)
    known_coverage = load_coverage_ids(args.metadata_dir)
    known_pressure = load_pressure_ids(args.metadata_dir)

    all_items: list[dict[str, Any]] = []
    schema_failures: list[dict[str, str]] = []

    for file_path in files:
        payload = _load_json(file_path)
        if isinstance(payload, dict) and "items" not in payload:
            print(f"[info] skipping non-batch JSON file: {file_path}")
            continue

        if isinstance(payload, dict) and "items" in payload:
            batch_errors = validate_batch(payload, batch_schema)
            schema_failures.extend(_render_schema_errors(file_path, batch_errors))

        items, extraction_issues = _extract_items(payload)
        schema_failures.extend(_render_schema_errors(file_path, extraction_issues))

        for item in items:
            item_errors = validate_item(item, item_schema)
            schema_failures.extend(_render_schema_errors(file_path, item_errors))
        all_items.extend(items)

    lint = run_lint_checks(
        all_items,
        known_dimensions=known_dimensions,
        known_coverage_tags=known_coverage,
        known_pressure_tags=known_pressure,
        near_duplicate_threshold=args.near_duplicate_threshold,
        pressure_concentration_threshold=args.pressure_concentration_threshold,
    )

    print(f"[info] validated files: {len(files)}")
    print(f"[info] total items inspected: {len(all_items)}")
    print(f"[info] schema issues: {len(schema_failures)}")
    print(f"[info] lint issues: {len(lint.issues)}")
    for failure in schema_failures:
        print(f"[error] {failure['path']}: {failure['error']}")

    _print_counter("Dimension coverage", lint.dimension_counts)
    _print_counter("Coverage tag distribution", lint.coverage_counts)
    _print_counter("Pressure tag distribution", lint.pressure_counts)

    for issue in lint.issues:
        ids = f" ({', '.join(issue.item_ids)})" if issue.item_ids else ""
        print(f"[{issue.severity}] {issue.code}{ids}: {issue.message}")

    report = {
        "files": [str(path) for path in files],
        "total_items": len(all_items),
        "schema_issue_count": len(schema_failures),
        "schema_issues": schema_failures,
        "lint_issue_count": len(lint.issues),
        "lint_issues": [issue.__dict__ for issue in lint.issues],
        "dimension_counts": lint.dimension_counts,
        "coverage_counts": lint.coverage_counts,
        "pressure_counts": lint.pressure_counts,
    }

    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[ok] wrote report to {args.report_json}")

    if schema_failures:
        raise SystemExit(1)
    if args.fail_on_warnings and lint.issues:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
