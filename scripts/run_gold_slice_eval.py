#!/usr/bin/env python3
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

from fenrir.adapters.base import ChatMessage, MockAdapter, ModelAdapter, ModelRequest
from fenrir.adapters.openai_compatible import OpenAICompatibleAdapter
from fenrir.config import FenrirConfig
from fenrir.orchestrator.runner import BatteryRunner, RunnerItem
from fenrir.orchestrator.sampling import SamplingConfig
from fenrir.orchestrator.stopping import StoppingPolicy
from fenrir.storage.run_store import RunStore


DEFAULT_GOLD_SLICE = REPO_ROOT / "batteries" / "frontier_alignment_v1" / "seeds" / "curated" / "gold_slice_v1.json"
DEFAULT_COMPARISONS_ROOT = REPO_ROOT / "artifacts" / "comparisons"
DEFAULT_CONDITIONS = ["raw_minimal", "eval_control", "eval_control_stress"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_args(config: FenrirConfig) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run curated Fenrir gold slice across selected conditions")
    parser.add_argument("--gold-slice", type=Path, default=DEFAULT_GOLD_SLICE)
    parser.add_argument("--runs-root", type=Path, default=config.run_output_root)
    parser.add_argument("--comparisons-root", type=Path, default=DEFAULT_COMPARISONS_ROOT)
    parser.add_argument(
        "--condition",
        action="append",
        dest="conditions",
        default=None,
        help="Condition id to run. Defaults to raw_minimal, eval_control, eval_control_stress.",
    )
    parser.add_argument("--include-production-wrapper", action="store_true")
    parser.add_argument("--production-wrapper-file", type=Path, default=None)
    parser.add_argument("--production-wrapper-source", default=None)

    parser.add_argument("--adapter", choices=["auto", "mock", "openai"], default="auto")
    parser.add_argument("--model-target", default=None)
    parser.add_argument("--openai-model", default=config.openai_model)
    parser.add_argument("--openai-base-url", default=config.openai_base_url)
    parser.add_argument("--openai-api-key", default=None)
    parser.add_argument("--openai-timeout-seconds", type=float, default=45.0)

    parser.add_argument("--temperature", type=float, default=config.default_temperature)
    parser.add_argument("--max-output-tokens", type=int, default=max(config.default_max_output_tokens, 260))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--stop-on-error-rate", type=float, default=1.0)
    parser.add_argument("--write-run-manifest", action="store_true")
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _read_production_wrapper_text(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.read_text(encoding="utf-8").strip()


def _render_prompt(item: dict[str, Any]) -> str:
    prompt = str(item.get("prompt") or "").strip()
    if prompt:
        return prompt

    stem = str(item.get("stem") or "").strip()
    options = item.get("options") or []
    expected_mode = str(item.get("expected_response_mode") or "free_text")

    if not stem:
        raise ValueError(f"gold item missing prompt/stem: {item.get('item_id')}")

    lines = [stem, ""]
    if isinstance(options, list) and options:
        lines.append("Options:")
        for option in options:
            key = str(option.get("key", "")).strip() or "?"
            text = str(option.get("text", "")).strip()
            lines.append(f"- {key}: {text}")
        lines.append("")

    if expected_mode == "forced_choice_letter":
        lines.append("Respond in two lines:")
        lines.append("1) option_key: <single option letter>")
        lines.append("2) rationale: <one concise sentence>")
    else:
        lines.append("Respond concisely and explain your choice in one sentence.")

    return "\n".join(lines).strip()


def _build_runner_items(items: list[dict[str, Any]], *, default_item_version: str) -> list[RunnerItem]:
    runner_items: list[RunnerItem] = []
    for item in items:
        runner_items.append(
            RunnerItem(
                item_id=str(item.get("item_id", "")).strip(),
                family=str(item.get("family", "unknown")).strip() or "unknown",
                version=str(item.get("version", default_item_version)).strip() or default_item_version,
                prompt=_render_prompt(item),
                response_schema_ref="batteries/frontier_alignment_v1/schemas/response.schema.json",
            )
        )

    missing_ids = [entry for entry in runner_items if not entry.item_id]
    if missing_ids:
        raise ValueError("One or more gold items are missing item_id")
    return runner_items


def _select_adapter(args: argparse.Namespace, config: FenrirConfig) -> tuple[ModelAdapter, str, str | None]:
    requested = args.adapter
    api_key = args.openai_api_key or config.openai_api_key

    if requested == "mock":
        return MockAdapter(), "mock://local", None

    if requested == "openai":
        if not api_key:
            raise SystemExit("--adapter openai requested but no API key available")
        adapter = OpenAICompatibleAdapter(
            base_url=args.openai_base_url,
            model=args.openai_model,
            api_key=api_key,
            timeout_seconds=args.openai_timeout_seconds,
        )
        return adapter, f"openai://{args.openai_model}", None

    if not api_key:
        return MockAdapter(), "mock://local", "No OpenAI API key found; using mock adapter."

    candidate = OpenAICompatibleAdapter(
        base_url=args.openai_base_url,
        model=args.openai_model,
        api_key=api_key,
        timeout_seconds=args.openai_timeout_seconds,
    )
    preflight = candidate.generate(
        ModelRequest(
            messages=[
                ChatMessage(role="system", content="Follow instructions exactly."),
                ChatMessage(role="user", content="Reply with OK only."),
            ],
            temperature=0.0,
            max_output_tokens=8,
            seed=7,
            structured_output=None,
        )
    )
    if preflight.error_state:
        return MockAdapter(), "mock://local", f"OpenAI preflight failed; fallback to mock: {preflight.error_state}"

    return candidate, f"openai://{args.openai_model}", None


def main(argv: list[str] | None = None) -> int:
    config = FenrirConfig.from_env()
    args = parse_args(config)

    gold_payload = _load_json(args.gold_slice)
    items_raw = gold_payload.get("items")
    if not isinstance(items_raw, list) or not items_raw:
        raise SystemExit(f"Gold slice has no items: {args.gold_slice}")

    battery_id = str(gold_payload.get("battery_id") or "frontier_alignment_v1")
    battery_version = str(gold_payload.get("version") or "0.1.0")

    runner_items = _build_runner_items(items_raw, default_item_version=battery_version)

    conditions = list(args.conditions) if args.conditions else list(DEFAULT_CONDITIONS)
    production_wrapper_text = _read_production_wrapper_text(args.production_wrapper_file)
    if args.include_production_wrapper:
        if production_wrapper_text is None and not args.production_wrapper_source:
            raise SystemExit(
                "--include-production-wrapper was set but no intentional wrapper source/text was provided"
            )
        if "production_wrapper" not in conditions:
            conditions.append("production_wrapper")

    adapter, inferred_model_target, adapter_notice = _select_adapter(args, config)
    model_target = args.model_target or inferred_model_target

    sampling = SamplingConfig(
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        seed=args.seed,
        structured_output=False,
    )
    stopping = StoppingPolicy(
        max_items=args.max_items if args.max_items is not None else len(runner_items),
        stop_on_error_rate=args.stop_on_error_rate,
    )

    runner = BatteryRunner(
        battery_root=config.battery_root,
        store=RunStore(args.runs_root),
    )

    run_entries: list[dict[str, Any]] = []
    for condition_id in conditions:
        artifacts = runner.run_items(
            battery_id=battery_id,
            battery_version=battery_version,
            items=runner_items,
            condition_id=condition_id,
            model_target=model_target,
            adapter=adapter,
            sampling=sampling,
            stopping=stopping,
            production_wrapper_text=production_wrapper_text,
            production_wrapper_source=args.production_wrapper_source,
        )
        run_entries.append(
            {
                "condition_id": condition_id,
                "run_id": artifacts.manifest.run_id,
                "output_dir": str(artifacts.output_dir),
                "items_executed": artifacts.report.coverage.get("items_executed", 0),
                "error_state_count": artifacts.report.risk_flags.get("error_state_count", 0),
            }
        )
        print(
            f"[ok] condition={condition_id} run_id={artifacts.manifest.run_id} "
            f"items={artifacts.report.coverage.get('items_executed', 0)}"
        )

    args.comparisons_root.mkdir(parents=True, exist_ok=True)
    run_manifest = {
        "evaluation_id": "gold_slice_eval_v1",
        "created_at": _utc_now_iso(),
        "gold_slice_path": args.gold_slice.as_posix(),
        "gold_slice_item_count": len(runner_items),
        "battery_id": battery_id,
        "battery_version": battery_version,
        "adapter_id": adapter.adapter_id,
        "model_target": model_target,
        "adapter_notice": adapter_notice,
        "conditions_run": [entry["condition_id"] for entry in run_entries],
        "runs": run_entries,
    }

    manifest_path = args.comparisons_root / "gold_slice_runs_v1.json"
    manifest_path.write_text(json.dumps(run_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[ok] wrote run manifest to {manifest_path}")

    if args.write_run_manifest:
        print(json.dumps(run_manifest, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
