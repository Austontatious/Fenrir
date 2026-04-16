from __future__ import annotations

from collections import defaultdict
import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def _stringify_list(values: Iterable[str]) -> str:
    clean = [value.strip() for value in values if isinstance(value, str) and value.strip()]
    return ", ".join(clean)


def _flatten_rows(items: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in items:
        options = item.get("options") or []
        option_text = " | ".join(
            f"{opt.get('key', '')}:{opt.get('text', '')}" for opt in options if isinstance(opt, Mapping)
        )
        scoring_stub = item.get("scoring_stub") or {}
        rows.append(
            {
                "item_id": str(item.get("item_id", "")),
                "battery_id": str(item.get("battery_id", "")),
                "version": str(item.get("version", "")),
                "family": str(item.get("family", "")),
                "stem": str(item.get("stem", "")),
                "options": option_text,
                "target_dimensions": _stringify_list(item.get("target_dimensions", [])),
                "coverage_tags": _stringify_list(item.get("coverage_tags", [])),
                "pressure_tags": _stringify_list(item.get("pressure_tags", [])),
                "variant_group": str(item.get("variant_group", "")),
                "expected_response_mode": str(item.get("expected_response_mode", "")),
                "scoring_primary_signal": str(scoring_stub.get("primary_signal", "")),
                "scoring_rationale": str(scoring_stub.get("rationale", "")),
                "review_status": str(item.get("review_status", "")),
                "generation_prompt_version": str(item.get("generation_prompt_version", "")),
                "generator_model": str(item.get("generator_model", "")),
                "notes": str(item.get("notes", "")),
            }
        )
    return rows


def render_markdown_review_packet(
    items: list[Mapping[str, Any]],
    *,
    title: str = "Fenrir Seed Review Packet",
) -> str:
    grouped: dict[str, dict[str, dict[str, dict[str, list[Mapping[str, Any]]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )

    for item in items:
        family = str(item.get("family", "unknown"))
        dimensions = item.get("target_dimensions") or ["unspecified"]
        coverages = item.get("coverage_tags") or ["unspecified"]
        pressures = item.get("pressure_tags") or ["unspecified"]

        for dimension in dimensions:
            for coverage in coverages:
                for pressure in pressures:
                    grouped[family][str(dimension)][str(coverage)][str(pressure)].append(item)

    lines: list[str] = [
        f"# {title}",
        "",
        "Generated items in this packet are draft seed content and require human review before curation.",
        "",
        "Review actions: `accept`, `edit`, `reject`, `rewrite`.",
    ]

    for family in sorted(grouped):
        lines.append("")
        lines.append(f"## Family: `{family}`")
        for dimension in sorted(grouped[family]):
            lines.append("")
            lines.append(f"### Target Dimension: `{dimension}`")
            for coverage in sorted(grouped[family][dimension]):
                lines.append("")
                lines.append(f"#### Coverage Tag: `{coverage}`")
                for pressure in sorted(grouped[family][dimension][coverage]):
                    lines.append("")
                    lines.append(f"##### Pressure Tag: `{pressure}`")
                    for item in grouped[family][dimension][coverage][pressure]:
                        item_id = str(item.get("item_id", "unknown"))
                        lines.append("")
                        lines.append(f"- Item `{item_id}`")
                        lines.append("  - Review: [ ] accept [ ] edit [ ] reject [ ] rewrite")
                        lines.append(f"  - Stem: {item.get('stem', '')}")
                        options = item.get("options") or []
                        if options:
                            lines.append("  - Options:")
                            for opt in options:
                                if isinstance(opt, Mapping):
                                    lines.append(
                                        f"    - {opt.get('key', '')}: {opt.get('text', '')}"
                                    )
                        lines.append(
                            "  - Target dimensions: "
                            + _stringify_list(item.get("target_dimensions", []))
                        )
                        lines.append(
                            "  - Coverage tags: "
                            + _stringify_list(item.get("coverage_tags", []))
                        )
                        lines.append(
                            "  - Pressure tags: "
                            + _stringify_list(item.get("pressure_tags", []))
                        )
                        lines.append(f"  - Variant group: {item.get('variant_group', '')}")
                        lines.append(
                            f"  - Expected response mode: {item.get('expected_response_mode', '')}"
                        )
                        scoring_stub = item.get("scoring_stub") or {}
                        lines.append(
                            f"  - Scoring primary signal: {scoring_stub.get('primary_signal', '')}"
                        )
                        lines.append(
                            f"  - Scoring rationale: {scoring_stub.get('rationale', '')}"
                        )
                        lines.append(f"  - Review status: {item.get('review_status', '')}")
                        lines.append(
                            f"  - Prompt version: {item.get('generation_prompt_version', '')}"
                        )
                        lines.append(f"  - Generator model: {item.get('generator_model', '')}")
                        lines.append(f"  - Notes: {item.get('notes', '')}")

    lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_markdown_review_packet(
    *,
    items: list[Mapping[str, Any]],
    output_path: Path,
    title: str = "Fenrir Seed Review Packet",
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    packet = render_markdown_review_packet(items, title=title)
    output_path.write_text(packet, encoding="utf-8")
    return output_path


def write_csv_export(*, items: list[Mapping[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = _flatten_rows(items)
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return output_path

    fieldnames = list(rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def write_jsonl_export(*, items: list[Mapping[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in _flatten_rows(items):
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return output_path
