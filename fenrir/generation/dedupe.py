from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re
from typing import Any, Iterable, Mapping


@dataclass
class LintIssue:
    code: str
    severity: str
    message: str
    item_ids: list[str] = field(default_factory=list)


@dataclass
class LintSummary:
    issues: list[LintIssue]
    dimension_counts: dict[str, int]
    coverage_counts: dict[str, int]
    pressure_counts: dict[str, int]

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")


def _normalize_text(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _token_set(value: str) -> set[str]:
    return set(_normalize_text(value).split())


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def dedupe_items(
    items: Iterable[Mapping[str, Any]],
    *,
    threshold: float = 0.92,
) -> tuple[list[dict[str, Any]], list[LintIssue]]:
    unique_items: list[dict[str, Any]] = []
    issues: list[LintIssue] = []

    for item in items:
        stem = str(item.get("stem", ""))
        stem_tokens = _token_set(stem)
        is_duplicate = False
        for existing in unique_items:
            sim = _jaccard(stem_tokens, _token_set(str(existing.get("stem", ""))))
            if sim >= threshold:
                issues.append(
                    LintIssue(
                        code="dedupe_near_duplicate_drop",
                        severity="warning",
                        message=f"Dropped near-duplicate stem at similarity {sim:.2f}",
                        item_ids=[
                            str(item.get("item_id", "unknown")),
                            str(existing.get("item_id", "unknown")),
                        ],
                    )
                )
                is_duplicate = True
                break
        if not is_duplicate:
            unique_items.append(dict(item))

    return unique_items, issues


def run_lint_checks(
    items: list[Mapping[str, Any]],
    *,
    known_dimensions: Iterable[str] | None = None,
    known_coverage_tags: Iterable[str] | None = None,
    known_pressure_tags: Iterable[str] | None = None,
    near_duplicate_threshold: float = 0.88,
    pressure_concentration_threshold: float = 0.55,
) -> LintSummary:
    issues: list[LintIssue] = []
    dimension_counts: Counter[str] = Counter()
    coverage_counts: Counter[str] = Counter()
    pressure_counts: Counter[str] = Counter()

    required_fields = {
        "item_id",
        "battery_id",
        "version",
        "family",
        "stem",
        "options",
        "target_dimensions",
        "coverage_tags",
        "pressure_tags",
        "variant_group",
        "expected_response_mode",
        "scoring_stub",
        "review_status",
        "generation_prompt_version",
        "generator_model",
        "notes",
    }

    stems: list[tuple[str, set[str], str]] = []
    option_structures: Counter[str] = Counter()
    moralizing_re = re.compile(
        r"\b(always|never|obviously|good person|bad person|moral duty|ethical duty|right thing)\b",
        flags=re.IGNORECASE,
    )

    for item in items:
        item_id = str(item.get("item_id", "unknown"))
        missing = sorted(field for field in required_fields if field not in item)
        if missing:
            issues.append(
                LintIssue(
                    code="schema_completeness_missing_fields",
                    severity="error",
                    message=f"Missing required fields: {', '.join(missing)}",
                    item_ids=[item_id],
                )
            )

        stem = str(item.get("stem", "")).strip()
        stems.append((item_id, _token_set(stem), stem))

        options = item.get("options")
        if isinstance(options, list):
            signature_parts = [str(len(options))]
            for opt in options:
                if isinstance(opt, Mapping):
                    signature_parts.append(_normalize_text(str(opt.get("text", "")))[:50])
            option_structures["|".join(signature_parts)] += 1

        if moralizing_re.search(stem):
            issues.append(
                LintIssue(
                    code="overly_obvious_moralizing",
                    severity="warning",
                    message="Stem contains likely moralizing language that may reduce discriminative value.",
                    item_ids=[item_id],
                )
            )

        for dimension in item.get("target_dimensions", []) or []:
            if isinstance(dimension, str) and dimension.strip():
                dimension_counts[dimension.strip()] += 1

        for coverage in item.get("coverage_tags", []) or []:
            if isinstance(coverage, str) and coverage.strip():
                coverage_counts[coverage.strip()] += 1

        pressure_tags = item.get("pressure_tags", []) or []
        if not pressure_tags:
            issues.append(
                LintIssue(
                    code="missing_pressure_tags",
                    severity="warning",
                    message="Item has no pressure_tags.",
                    item_ids=[item_id],
                )
            )
        for pressure in pressure_tags:
            if isinstance(pressure, str) and pressure.strip():
                pressure_counts[pressure.strip()] += 1

        if not str(item.get("variant_group", "")).strip():
            issues.append(
                LintIssue(
                    code="missing_variant_group",
                    severity="warning",
                    message="variant_group is empty.",
                    item_ids=[item_id],
                )
            )

    for i in range(len(stems)):
        left_id, left_tokens, left_stem = stems[i]
        for j in range(i + 1, len(stems)):
            right_id, right_tokens, right_stem = stems[j]
            similarity = _jaccard(left_tokens, right_tokens)
            if similarity >= near_duplicate_threshold:
                issues.append(
                    LintIssue(
                        code="near_duplicate_stem",
                        severity="warning",
                        message=(
                            f"Near-duplicate stems detected (similarity={similarity:.2f}): "
                            f"'{left_stem[:80]}' vs '{right_stem[:80]}'"
                        ),
                        item_ids=[left_id, right_id],
                    )
                )

    for signature, count in option_structures.items():
        if count >= 3 and signature:
            issues.append(
                LintIssue(
                    code="repeated_option_structure",
                    severity="warning",
                    message=f"Option structure repeated {count} times: {signature[:120]}",
                    item_ids=[],
                )
            )

    total_items = max(1, len(items))

    if known_dimensions is not None:
        for dim in sorted(set(known_dimensions)):
            if dim and dimension_counts.get(dim, 0) == 0:
                issues.append(
                    LintIssue(
                        code="target_dimension_gap",
                        severity="warning",
                        message=f"No generated items for target dimension '{dim}'.",
                        item_ids=[],
                    )
                )

    if known_coverage_tags is not None:
        for tag in sorted(set(known_coverage_tags)):
            if tag and coverage_counts.get(tag, 0) == 0:
                issues.append(
                    LintIssue(
                        code="coverage_tag_gap",
                        severity="warning",
                        message=f"No generated items for coverage tag '{tag}'.",
                        item_ids=[],
                    )
                )

    if known_pressure_tags is not None:
        for tag in sorted(set(known_pressure_tags)):
            if tag and pressure_counts.get(tag, 0) == 0:
                issues.append(
                    LintIssue(
                        code="pressure_tag_gap",
                        severity="warning",
                        message=f"No generated items for pressure tag '{tag}'.",
                        item_ids=[],
                    )
                )

    if pressure_counts:
        most_common_tag, most_common_count = pressure_counts.most_common(1)[0]
        concentration = most_common_count / total_items
        if concentration > pressure_concentration_threshold:
            issues.append(
                LintIssue(
                    code="pressure_tag_overconcentration",
                    severity="warning",
                    message=(
                        f"Pressure tag '{most_common_tag}' appears in "
                        f"{most_common_count}/{total_items} items ({concentration:.0%})."
                    ),
                    item_ids=[],
                )
            )

    return LintSummary(
        issues=issues,
        dimension_counts=dict(dimension_counts),
        coverage_counts=dict(coverage_counts),
        pressure_counts=dict(pressure_counts),
    )
