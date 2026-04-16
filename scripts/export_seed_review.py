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
from fenrir.generation.review_export import (
    write_csv_export,
    write_jsonl_export,
    write_markdown_review_packet,
)


DEFAULT_GENERATED_DIR = REPO_ROOT / "batteries" / DEFAULT_BATTERY_ID / "seeds" / "generated"
DEFAULT_REVIEW_DIR = REPO_ROOT / "batteries" / DEFAULT_BATTERY_ID / "seeds" / "review"


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
    files = _discover_json_files(args.input)
    if not files:
        raise SystemExit(f"No JSON seed files found at {args.input}")

    items: list[dict[str, Any]] = []
    for path in files:
        items.extend(_extract_items(_load_payload(path)))

    if not items:
        raise SystemExit("No seed items found in the supplied input files")

    write_markdown_review_packet(items=items, output_path=args.markdown_out, title=args.title)
    print(f"[ok] markdown review packet: {args.markdown_out}")

    if args.csv_out is not None:
        write_csv_export(items=items, output_path=args.csv_out)
        print(f"[ok] csv export: {args.csv_out}")

    if args.jsonl_out is not None:
        write_jsonl_export(items=items, output_path=args.jsonl_out)
        print(f"[ok] jsonl export: {args.jsonl_out}")


if __name__ == "__main__":
    main()
