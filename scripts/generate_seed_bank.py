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
    ensure_within_allowed_roots,
    load_coverage_ids,
    load_dimension_ids,
    load_pressure_ids,
    load_seed_batch_schema,
    seed_surface_paths,
    load_sensitivity_ids,
    require_valid_batch,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _as_output_path(path: Path, *, timestamp: str) -> Path:
    if path.suffix.lower() == ".json":
        return path
    return path / f"seed_batch_{timestamp}.json"


def _write_json(path: Path, payload: Any, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file without --overwrite: {path}")
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
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--artifact-dir", type=Path, default=None)
    parser.add_argument("--schema-dir", type=Path, default=None)
    parser.add_argument("--metadata-dir", type=Path, default=None)
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
    parser.add_argument("--fixture-path", type=Path, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned output locations and generation plan without writing files or calling model APIs.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing to output paths that already exist.",
    )
    parser.add_argument(
        "--allow-external-output",
        action="store_true",
        help="Allow output/artifact paths outside the canonical batteries/<battery>/seeds surface.",
    )
    return parser.parse_args()


def main() -> None:
    config = FenrirConfig.from_env()
    args = parse_args(config)

    if args.count <= 0:
        raise SystemExit("--count must be positive")

    timestamp = _utc_timestamp()
    surface = seed_surface_paths(battery_id=args.battery_id)

    output_arg = args.output or surface.generated_root
    output_path = _as_output_path(output_arg.resolve(), timestamp=timestamp)
    artifact_dir = (args.artifact_dir or (surface.generated_raw_root / timestamp)).resolve()
    schema_dir = (args.schema_dir or surface.schemas_root).resolve()
    metadata_dir = (args.metadata_dir or surface.metadata_root).resolve()
    fixture_path = (args.fixture_path or (surface.generated_root / "sample_seed_batch.json")).resolve()

    if not args.allow_external_output:
        output_path = ensure_within_allowed_roots(
            output_path,
            allowed_roots=[surface.generated_root],
            label="output",
        )
        artifact_dir = ensure_within_allowed_roots(
            artifact_dir,
            allowed_roots=[surface.generated_raw_root],
            label="artifact",
        )
        schema_dir = ensure_within_allowed_roots(
            schema_dir,
            allowed_roots=[surface.schemas_root],
            label="schema",
        )
        metadata_dir = ensure_within_allowed_roots(
            metadata_dir,
            allowed_roots=[surface.metadata_root],
            label="metadata",
        )
    else:
        output_path = output_path.resolve()
        artifact_dir = artifact_dir.resolve()

    seed_batch_schema = load_seed_batch_schema(schema_dir)

    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"Refusing to overwrite existing output without --overwrite: {output_path}")
    if artifact_dir.exists() and any(artifact_dir.iterdir()) and not args.overwrite:
        raise SystemExit(
            f"Refusing to write into non-empty artifact dir without --overwrite: {artifact_dir}"
        )

    print(f"[info] battery_id={args.battery_id}")
    print(f"[info] output_path={output_path}")
    print(f"[info] artifact_dir={artifact_dir}")
    print(f"[info] schema_dir={schema_dir}")
    print(f"[info] metadata_dir={metadata_dir}")

    if args.dry_run:
        print(f"[dry-run] would generate families={args.family} count_per_family={args.count}")
        print("[dry-run] no API calls and no file writes were performed")
        return

    api_key = args.api_key if args.api_key is not None else config.openai_api_key

    if not api_key:
        if not args.allow_fixture_fallback:
            raise SystemExit("Missing API key. Set FENRIR_OPENAI_API_KEY or pass --api-key.")
        fixture = _load_fixture_batch(fixture_path)
        require_valid_batch(fixture, seed_batch_schema)
        _write_json(output_path, fixture, overwrite=args.overwrite)
        print(f"[ok] API key missing; wrote fixture batch to {output_path}")
        return

    dimension_ids = load_dimension_ids(metadata_dir)
    coverage_ids = load_coverage_ids(metadata_dir)
    pressure_ids = load_pressure_ids(metadata_dir)
    sensitivity_ids = load_sensitivity_ids(metadata_dir)

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
        _write_json(family_dir / "request.json", result.request_payload, overwrite=args.overwrite)
        _write_json(family_dir / "response.json", result.response_payload, overwrite=args.overwrite)
        (family_dir / "raw_output_text.txt").write_text(result.raw_text, encoding="utf-8")
        _write_json(
            family_dir / "prompt_meta.json",
            {
                "prompt_name": result.prompt_name,
                "prompt_sha256": result.prompt_sha256,
                "prompt_version": result.prompt_version,
            },
            overwrite=args.overwrite,
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

    _write_json(output_path, final_batch, overwrite=args.overwrite)
    if dedupe_issues:
        _write_json(
            artifact_dir / "dedupe_report.json",
            {
                "dropped_count": len(dedupe_issues),
                "issues": [issue.__dict__ for issue in dedupe_issues],
            },
            overwrite=args.overwrite,
        )

    print(f"[ok] wrote {len(final_items)} items to {output_path}")
    print(f"[ok] raw generation artifacts stored in {artifact_dir}")


if __name__ == "__main__":
    main()
