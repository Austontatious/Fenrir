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

from fenrir.reports.gold_slice_eval import build_gold_slice_comparison, build_item_diagnostics
from fenrir.storage.run_store import RunStore


DEFAULT_RUN_MANIFEST = REPO_ROOT / "artifacts" / "comparisons" / "gold_slice_runs_v1.json"
DEFAULT_COMPARISONS_ROOT = REPO_ROOT / "artifacts" / "comparisons"
DEFAULT_DOC_REPORT = DEFAULT_COMPARISONS_ROOT / "gold_slice_eval_report.md"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare curated gold-slice condition runs")
    parser.add_argument("--run-manifest", type=Path, default=DEFAULT_RUN_MANIFEST)
    parser.add_argument("--runs-root", type=Path, default=REPO_ROOT / "artifacts" / "runs")
    parser.add_argument("--comparisons-root", type=Path, default=DEFAULT_COMPARISONS_ROOT)
    parser.add_argument("--doc-report", type=Path, default=DEFAULT_DOC_REPORT)
    parser.add_argument(
        "--write-doc-report",
        action="store_true",
        help="Write long-form markdown report. Default skips this extra write.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object payload at {path}")
    return payload


def _render_eval_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Gold Slice Evaluation Summary")
    lines.append("")
    lines.append(f"- generated_at: `{payload['generated_at']}`")
    lines.append(f"- model_target: `{payload['model_target']}`")
    lines.append(f"- adapter_id: `{payload['adapter_id']}`")
    lines.append(f"- conditions_run: `{', '.join(payload['conditions_run'])}`")
    lines.append("")

    notice = payload.get("adapter_notice")
    if notice:
        lines.append("## Adapter Notice")
        lines.append(notice)
        lines.append("")

    lines.append("## Overall By Condition")
    for condition_id, info in payload["overall_by_condition"].items():
        lines.append(f"### {condition_id}")
        lines.append(f"- run_id: `{info['run_id']}`")
        lines.append(f"- items_executed: {info['items_executed']}")
        lines.append(f"- mean_latency_ms: {info['mean_latency_ms']}")
        lines.append(f"- non_error_rate: {info['non_error_rate']}")
        lines.append(f"- fragility_rate: {info['fragility_rate']}")

    lines.append("")
    lines.append("## Wrapper Dependence")
    wd = payload["wrapper_dependence"]
    lines.append(f"- index: {wd['index']}")
    lines.append(f"- bucket: {wd['bucket']}")
    lines.append(f"- explanation: {wd['explanation']}")
    for key, value in wd.get("pair_deltas", {}).items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("## Stress Fragility")
    if payload["stress_fragility"]:
        for key, value in payload["stress_fragility"].items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- eval_control and eval_control_stress pair not both present")

    lines.append("")
    lines.append("## Top Condition Deltas")
    for item in payload["top_condition_deltas"]:
        lines.append(
            f"- {item['pair']} {item['metric']}: delta={item['delta']} (abs={item['abs_delta']})"
        )
    lines.append("")
    return "\n".join(lines)


def _render_diagnostics_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Gold Slice Item Diagnostics")
    lines.append("")
    summary = payload["summary_counts"]
    lines.append(
        "- classification counts: "
        + ", ".join(f"{key}={value}" for key, value in sorted(summary.items()))
    )
    lines.append("")
    lines.append("| item_id | family | class | separation | uniqueness | reason |")
    lines.append("|---|---|---|---:|---:|---|")
    for item in payload["items"]:
        lines.append(
            "| {item_id} | {family} | {classification} | {separation_score} | {response_uniqueness} | {reason} |".format(
                **item
            )
        )
    lines.append("")
    return "\n".join(lines)


def _render_doc_report(eval_payload: dict[str, Any], diag_payload: dict[str, Any]) -> str:
    counts = diag_payload["summary_counts"]
    keep = counts.get("keep", 0)
    revise = counts.get("revise", 0)
    demote = counts.get("demote", 0)
    unclear = counts.get("unclear", 0)

    instrument_like = keep >= 6 and eval_payload["wrapper_dependence"]["index"] >= 0.1
    recommendation = "expand cautiously" if instrument_like else "revise/recalibrate before expansion"

    lines: list[str] = []
    lines.append("# Gold Slice Evaluation Report")
    lines.append("")
    lines.append(f"Date: {_utc_now_iso()}")
    lines.append("")
    lines.append("## Conditions Run")
    lines.append("- " + "\n- ".join(eval_payload["conditions_run"]))
    lines.append("")
    lines.append("## Model Target")
    lines.append(f"- `{eval_payload['model_target']}` via `{eval_payload['adapter_id']}`")
    if eval_payload.get("adapter_notice"):
        lines.append(f"- adapter notice: {eval_payload['adapter_notice']}")
    lines.append("")

    lines.append("## Top Observed Deltas")
    top = eval_payload["top_condition_deltas"][:5]
    if top:
        for row in top:
            lines.append(
                f"- {row['pair']} {row['metric']}: delta={row['delta']} (abs={row['abs_delta']})"
            )
    else:
        lines.append("- No meaningful deltas observed.")
    lines.append("")

    lines.append("## Wrapper Dependence")
    wd = eval_payload["wrapper_dependence"]
    lines.append(f"- index: {wd['index']}")
    lines.append(f"- bucket: {wd['bucket']}")
    lines.append(f"- explanation: {wd['explanation']}")
    lines.append("")

    lines.append("## Item-Level Diagnostics")
    lines.append(f"- keep: {keep}")
    lines.append(f"- revise: {revise}")
    lines.append(f"- demote: {demote}")
    lines.append(f"- unclear: {unclear}")
    lines.append("")

    lines.append("## Instrument Assessment")
    if instrument_like:
        lines.append("Fenrir shows instrument-like behavior on this slice with condition-sensitive signal on multiple items.")
    else:
        lines.append("Fenrir remains partially scaffold-like on this slice; signal exists but item quality/trace reliability needs further tightening.")
    lines.append("")

    lines.append("## Recommendation")
    lines.append(f"- Next step: **{recommendation}**")
    lines.append("")

    lines.append("## Caveats")
    lines.append("- This phase uses only curated `gold_slice_v1`; no broad seed expansion was run.")
    lines.append("- Scores remain rubric-stub and should be interpreted as behavioral telemetry, not alignment proof.")
    lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args()
    run_manifest = _load_json(args.run_manifest)

    runs = run_manifest.get("runs")
    if not isinstance(runs, list) or not runs:
        raise SystemExit(f"No runs found in {args.run_manifest}")

    store = RunStore(args.runs_root)

    condition_reports: dict[str, dict[str, object]] = {}
    condition_responses: dict[str, dict[str, object]] = {}
    overall_by_condition: dict[str, dict[str, object]] = {}

    for entry in runs:
        if not isinstance(entry, dict):
            continue
        condition_id = str(entry.get("condition_id", "")).strip()
        run_id = str(entry.get("run_id", "")).strip()
        if not condition_id or not run_id:
            continue

        manifest = store.load_manifest(run_id)
        report = store.load_report(run_id)
        responses = store.load_responses(run_id)

        condition_reports[condition_id] = report.model_dump()
        condition_responses[condition_id] = {response.item_id: response for response in responses}
        overall_by_condition[condition_id] = {
            "run_id": run_id,
            "items_executed": report.coverage.get("items_executed", 0),
            "mean_latency_ms": report.stability_metrics.get("mean_latency_ms", 0.0),
            "non_error_rate": report.stability_metrics.get("non_error_rate", 0.0),
            "fragility_rate": report.stability_metrics.get("fragility_rate", 0.0),
            "condition_version": manifest.condition_version,
            "system_prompt_hash": manifest.system_prompt_hash,
        }

    comparison = build_gold_slice_comparison(condition_reports)
    diagnostics, summary_counts = build_item_diagnostics(condition_responses)

    args.comparisons_root.mkdir(parents=True, exist_ok=True)

    eval_payload = {
        "evaluation_id": "gold_slice_eval_v1",
        "generated_at": _utc_now_iso(),
        "model_target": run_manifest.get("model_target", "unknown"),
        "adapter_id": run_manifest.get("adapter_id", "unknown"),
        "adapter_notice": run_manifest.get("adapter_notice"),
        "conditions_run": run_manifest.get("conditions_run", []),
        "run_manifest_path": args.run_manifest.as_posix(),
        "overall_by_condition": overall_by_condition,
        "wrapper_dependence": comparison.wrapper_dependence.model_dump(),
        "stress_fragility": comparison.stress_fragility,
        "top_condition_deltas": comparison.top_condition_deltas,
        "caveats": [
            "Condition comparisons are valid only for runs sharing the same battery and item set.",
            "Trace scoring is rubric-stub and should be treated as interpretable telemetry.",
        ],
    }

    diagnostics_payload = {
        "evaluation_id": "gold_slice_item_diagnostics_v1",
        "generated_at": _utc_now_iso(),
        "summary_counts": summary_counts,
        "items": [
            {
                "item_id": item.item_id,
                "family": item.family,
                "classification": item.classification,
                "reason": item.reason,
                "separation_score": item.separation_score,
                "response_uniqueness": item.response_uniqueness,
                "low_confidence_ratio": item.low_confidence_ratio,
                "ambiguity_ratio": item.ambiguity_ratio,
                "evidence_presence_ratio": item.evidence_presence_ratio,
                "conditions_present": item.conditions_present,
            }
            for item in diagnostics
        ],
    }

    eval_json = args.comparisons_root / "gold_slice_eval_v1.json"
    eval_md = args.comparisons_root / "gold_slice_eval_v1.md"
    diag_json = args.comparisons_root / "gold_slice_item_diagnostics_v1.json"
    diag_md = args.comparisons_root / "gold_slice_item_diagnostics_v1.md"

    eval_json.write_text(json.dumps(eval_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    eval_md.write_text(_render_eval_markdown(eval_payload), encoding="utf-8")
    diag_json.write_text(json.dumps(diagnostics_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    diag_md.write_text(_render_diagnostics_markdown(diagnostics_payload), encoding="utf-8")

    print(f"[ok] wrote {eval_json}")
    print(f"[ok] wrote {eval_md}")
    print(f"[ok] wrote {diag_json}")
    print(f"[ok] wrote {diag_md}")
    if args.write_doc_report:
        args.doc_report.parent.mkdir(parents=True, exist_ok=True)
        args.doc_report.write_text(_render_doc_report(eval_payload, diagnostics_payload), encoding="utf-8")
        print(f"[ok] wrote {args.doc_report}")
    else:
        print("[info] skipped --write-doc-report (no long-form doc write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
