#!/usr/bin/env python3
"""Export Fenrir seeds into human-review packets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fenrir.generation import DEFAULT_BATTERY_ID
from fenrir.generation.paths import ensure_within_allowed_roots, seed_surface_paths
from fenrir.generation.review_export import (
    write_csv_export,
    write_jsonl_export,
    write_markdown_review_packet,
)


DEFAULT_SURFACE = seed_surface_paths(battery_id=DEFAULT_BATTERY_ID)
DEFAULT_GENERATED_DIR = DEFAULT_SURFACE.generated_root
DEFAULT_REVIEW_DIR = DEFAULT_SURFACE.review_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Fenrir review packets")
    parser.add_argument("--input", type=Path, default=DEFAULT_GENERATED_DIR)
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=DEFAULT_REVIEW_DIR / "seed_review_packet.md",
    )
    parser.add_argument("--csv-out", type=Path, default=None)
    parser.add_argument("--jsonl-out", type=Path, default=None)
    parser.add_argument("--title", default="Fenrir Seed Review Packet")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print destination paths without writing outputs.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing export files.",
    )
    parser.add_argument(
        "--allow-external-output",
        action="store_true",
        help="Allow output paths outside batteries/<battery>/seeds/review.",
    )
    return parser.parse_args()


def _discover_json_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    files = sorted(candidate for candidate in path.rglob("*.json") if candidate.is_file())
    return [candidate for candidate in files if "/raw/" not in candidate.as_posix()]


def _load_payload(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def main() -> None:
    args = parse_args()
    surface = seed_surface_paths(battery_id=DEFAULT_BATTERY_ID)
    input_path = args.input.resolve()
    markdown_out = args.markdown_out.resolve()
    csv_out = args.csv_out.resolve() if args.csv_out is not None else None
    jsonl_out = args.jsonl_out.resolve() if args.jsonl_out is not None else None

    if not args.allow_external_output:
        input_path = ensure_within_allowed_roots(
            input_path,
            allowed_roots=[surface.generated_root, surface.curated_root],
            label="input",
        )
        markdown_out = ensure_within_allowed_roots(
            markdown_out,
            allowed_roots=[surface.review_root],
            label="markdown output",
        )
        if csv_out is not None:
            csv_out = ensure_within_allowed_roots(
                csv_out,
                allowed_roots=[surface.review_root],
                label="csv output",
            )
        if jsonl_out is not None:
            jsonl_out = ensure_within_allowed_roots(
                jsonl_out,
                allowed_roots=[surface.review_root],
                label="jsonl output",
            )

    for target in [markdown_out, csv_out, jsonl_out]:
        if target is not None and target.exists() and not args.overwrite:
            raise SystemExit(f"Refusing to overwrite existing file without --overwrite: {target}")

    print(f"[info] input={input_path}")
    print(f"[info] markdown_out={markdown_out}")
    if csv_out is not None:
        print(f"[info] csv_out={csv_out}")
    if jsonl_out is not None:
        print(f"[info] jsonl_out={jsonl_out}")

    files = _discover_json_files(input_path)
    if not files:
        raise SystemExit(f"No JSON seed files found at {input_path}")

    items: list[dict[str, Any]] = []
    for path in files:
        items.extend(_extract_items(_load_payload(path)))

    if not items:
        raise SystemExit("No seed items found in the supplied input files")

    if args.dry_run:
        print(f"[dry-run] would export {len(items)} seed items")
        print("[dry-run] no files written")
        return

    write_markdown_review_packet(items=items, output_path=markdown_out, title=args.title)
    print(f"[ok] markdown review packet: {markdown_out}")

    if csv_out is not None:
        write_csv_export(items=items, output_path=csv_out)
        print(f"[ok] csv export: {csv_out}")

    if jsonl_out is not None:
        write_jsonl_export(items=items, output_path=jsonl_out)
        print(f"[ok] jsonl export: {jsonl_out}")


if __name__ == "__main__":
    main()
