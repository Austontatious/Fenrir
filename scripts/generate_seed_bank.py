#!/usr/bin/env python3
"""Generate Fenrir draft seed-bank batches via OpenAI Responses structured outputs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.prompt_loader import PromptLoader
from fenrir.adapters.openai_compatible import OpenAICompatibleAdapter
from fenrir.config import FenrirConfig
from fenrir.generation import (
    DEFAULT_BATTERY_ID,
    PROMPT_VERSION,
    SUPPORTED_FAMILIES,
    OpenAISeedGenerator,
    SeedGenerationRequest,
    dedupe_items,
    load_coverage_ids,
    load_dimension_ids,
    load_pressure_ids,
    load_seed_batch_schema,
    load_sensitivity_ids,
    require_valid_batch,
)


DEFAULT_OUTPUT_DIR = REPO_ROOT / "batteries" / DEFAULT_BATTERY_ID / "seeds" / "generated"
DEFAULT_METADATA_DIR = REPO_ROOT / "batteries" / DEFAULT_BATTERY_ID / "metadata"
DEFAULT_SCHEMA_DIR = REPO_ROOT / "batteries" / DEFAULT_BATTERY_ID / "schemas"
DEFAULT_FIXTURE_PATH = DEFAULT_OUTPUT_DIR / "sample_seed_batch.json"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _as_output_path(path: Path, *, timestamp: str) -> Path:
    if path.suffix.lower() == ".json":
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    path.mkdir(parents=True, exist_ok=True)
    return path / f"seed_batch_{timestamp}.json"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_fixture_batch(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Fixture at {path} must be a JSON object")
    return payload


def parse_args(config: FenrirConfig) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Fenrir seed-bank batch files")
    parser.add_argument(
        "--family",
        action="append",
        required=True,
        choices=sorted(SUPPORTED_FAMILIES),
        help="Item family to generate. Can be provided multiple times.",
    )
    parser.add_argument("--count", type=int, required=True, help="Items per family")
    parser.add_argument("--battery-id", default=DEFAULT_BATTERY_ID)
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--model", default=config.openai_model)
    parser.add_argument("--base-url", default=config.openai_base_url)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--artifact-dir", type=Path, default=None)
    parser.add_argument("--schema-dir", type=Path, default=DEFAULT_SCHEMA_DIR)
    parser.add_argument("--metadata-dir", type=Path, default=DEFAULT_METADATA_DIR)
    parser.add_argument("--prompt-version", default=PROMPT_VERSION)
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Optional temperature override. Omit for model defaults.",
    )
    parser.add_argument("--max-output-tokens", type=int, default=3000)
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--dedupe-threshold", type=float, default=0.92)
    parser.add_argument("--keep-near-duplicates", action="store_true")
    parser.add_argument("--store", action="store_true", help="Enable OpenAI response storage")
    parser.add_argument(
        "--allow-fixture-fallback",
        action="store_true",
        help="Use sample fixture when API key is missing.",
    )
    parser.add_argument("--fixture-path", type=Path, default=DEFAULT_FIXTURE_PATH)
    return parser.parse_args()


def main() -> None:
    config = FenrirConfig.from_env()
    args = parse_args(config)

    if args.count <= 0:
        raise SystemExit("--count must be positive")

    seed_batch_schema = load_seed_batch_schema(args.schema_dir)
    timestamp = _utc_timestamp()

    output_path = _as_output_path(args.output, timestamp=timestamp)
    artifact_dir = args.artifact_dir
    if artifact_dir is None:
        artifact_dir = output_path.parent / "raw" / timestamp

    api_key = args.api_key if args.api_key is not None else config.openai_api_key

    if not api_key:
        if not args.allow_fixture_fallback:
            raise SystemExit("Missing API key. Set FENRIR_OPENAI_API_KEY or pass --api-key.")
        fixture = _load_fixture_batch(args.fixture_path)
        require_valid_batch(fixture, seed_batch_schema)
        _write_json(output_path, fixture)
        print(f"[ok] API key missing; wrote fixture batch to {output_path}")
        return

    dimension_ids = load_dimension_ids(args.metadata_dir)
    coverage_ids = load_coverage_ids(args.metadata_dir)
    pressure_ids = load_pressure_ids(args.metadata_dir)
    sensitivity_ids = load_sensitivity_ids(args.metadata_dir)

    adapter = OpenAICompatibleAdapter(
        base_url=args.base_url,
        model=args.model,
        api_key=api_key,
        timeout_seconds=args.timeout_seconds,
    )
    prompt_loader = PromptLoader(REPO_ROOT / "prompts")
    generator = OpenAISeedGenerator(
        adapter=adapter,
        prompt_loader=prompt_loader,
        seed_batch_schema=seed_batch_schema,
        generator_model=args.model,
    )

    all_items: list[dict[str, Any]] = []

    for family in args.family:
        request = SeedGenerationRequest(
            battery_id=args.battery_id,
            version=args.version,
            family=family,
            count=args.count,
            generation_prompt_version=args.prompt_version,
            dimension_ids=dimension_ids,
            coverage_ids=coverage_ids,
            pressure_ids=pressure_ids,
            sensitivity_ids=sensitivity_ids,
        )
        result = generator.generate(
            request,
            max_output_tokens=args.max_output_tokens,
            temperature=args.temperature,
            store=args.store,
        )
        all_items.extend(result.batch.get("items", []))

        family_dir = artifact_dir / family
        _write_json(family_dir / "request.json", result.request_payload)
        _write_json(family_dir / "response.json", result.response_payload)
        (family_dir / "raw_output_text.txt").write_text(result.raw_text, encoding="utf-8")
        _write_json(
            family_dir / "prompt_meta.json",
            {
                "prompt_name": result.prompt_name,
                "prompt_sha256": result.prompt_sha256,
                "prompt_version": result.prompt_version,
            },
        )
        print(f"[info] generated {len(result.batch.get('items', []))} {family} items")

    deduped_items, dedupe_issues = dedupe_items(all_items, threshold=args.dedupe_threshold)
    if dedupe_issues:
        print(f"[warn] dedupe dropped {len(dedupe_issues)} near-duplicate items")

    final_items = all_items if args.keep_near_duplicates else deduped_items

    final_batch = {
        "battery_id": args.battery_id,
        "version": args.version,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
        "generation_prompt_version": args.prompt_version,
        "generator_model": args.model,
        "items": final_items,
    }
    require_valid_batch(final_batch, seed_batch_schema)

    _write_json(output_path, final_batch)
    if dedupe_issues:
        _write_json(
            artifact_dir / "dedupe_report.json",
            {
                "dropped_count": len(dedupe_issues),
                "issues": [issue.__dict__ for issue in dedupe_issues],
            },
        )

    print(f"[ok] wrote {len(final_items)} items to {output_path}")
    print(f"[ok] raw generation artifacts stored in {artifact_dir}")


if __name__ == "__main__":
    main()
