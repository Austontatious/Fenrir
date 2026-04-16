from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import re
from typing import Any, Iterable, Mapping

from fenrir.generation.review_states import REVIEW_STATES


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
    review_status_counts: dict[str, int]

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


def _is_placeholder_note(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered:
        return True
    placeholder_patterns = [
        r"^n/?a$",
        r"^tbd$",
        r"^todo$",
        r"^draft seed generated for human review\.?$",
        r"^needs review$",
        r"^pending review$",
    ]
    return any(re.match(pattern, lowered) for pattern in placeholder_patterns)


def _option_text_lookup(options: list[Mapping[str, Any]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for option in options:
        key = str(option.get("key", "")).strip()
        text = str(option.get("text", "")).strip()
        if key:
            lookup[key] = text
    return lookup


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
    dimension_concentration_threshold: float = 0.45,
    coverage_concentration_threshold: float = 0.55,
    option_length_imbalance_ratio: float = 2.3,
    option_length_imbalance_delta: int = 45,
    repeated_opening_threshold: int = 3,
    repeated_moralized_token_threshold: int = 8,
    variant_group_overuse_threshold: int = 3,
) -> LintSummary:
    issues: list[LintIssue] = []
    dimension_counts: Counter[str] = Counter()
    coverage_counts: Counter[str] = Counter()
    pressure_counts: Counter[str] = Counter()
    review_status_counts: Counter[str] = Counter()

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
    opening_template_to_ids: dict[str, list[str]] = defaultdict(list)
    variant_group_counts: Counter[str] = Counter()
    variant_group_by_family: dict[str, Counter[str]] = defaultdict(Counter)
    moralized_token_counts: Counter[str] = Counter()

    moralizing_re = re.compile(
        r"\b(always|never|obviously|good person|bad person|moral duty|ethical duty|right thing)\b",
        flags=re.IGNORECASE,
    )
    moralized_tokens = {
        "obviously",
        "clearly",
        "ethical",
        "moral",
        "honest",
        "truthful",
        "safe",
        "responsible",
        "bad",
        "good",
    }
    positive_cues = {"transparent", "verify", "truthful", "honest", "safe", "responsible", "clear"}
    negative_cues = {"hide", "conceal", "bypass", "mislead", "deceive", "blame", "fabricate", "omit"}

    for item in items:
        item_id = str(item.get("item_id", "unknown"))
        family = str(item.get("family", "")).strip()
        review_status = str(item.get("review_status", "")).strip()
        review_status_counts[review_status or "missing"] += 1

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

        if review_status and review_status not in REVIEW_STATES:
            issues.append(
                LintIssue(
                    code="invalid_review_status",
                    severity="error",
                    message=f"Unknown review_status '{review_status}'.",
                    item_ids=[item_id],
                )
            )

        stem = str(item.get("stem", "")).strip()
        normalized_stem = _normalize_text(stem)
        stems.append((item_id, _token_set(stem), stem))

        opening_tokens = normalized_stem.split()[:6]
        if opening_tokens:
            opening_template_to_ids[" ".join(opening_tokens)].append(item_id)

        options = item.get("options")
        option_text_blobs: list[str] = []
        if isinstance(options, list):
            signature_parts = [str(len(options))]
            option_lengths: list[int] = []
            for opt in options:
                if isinstance(opt, Mapping):
                    option_text = str(opt.get("text", ""))
                    option_text_blobs.append(option_text)
                    normalized_option = _normalize_text(option_text)
                    signature_parts.append(normalized_option[:50])
                    option_lengths.append(len(option_text.strip()))
                    for token in normalized_option.split():
                        if token in moralized_tokens:
                            moralized_token_counts[token] += 1
            option_structures["|".join(signature_parts)] += 1

            if len(option_lengths) >= 2:
                shortest = max(1, min(option_lengths))
                longest = max(option_lengths)
                ratio = longest / shortest
                delta = longest - shortest
                if ratio > option_length_imbalance_ratio and delta >= option_length_imbalance_delta:
                    issues.append(
                        LintIssue(
                            code="option_length_imbalance",
                            severity="warning",
                            message=(
                                f"Options have length imbalance ratio={ratio:.2f} delta={delta}."
                            ),
                            item_ids=[item_id],
                        )
                    )

        for token in normalized_stem.split():
            if token in moralized_tokens:
                moralized_token_counts[token] += 1

        if moralizing_re.search(stem):
            issues.append(
                LintIssue(
                    code="overly_obvious_moralizing",
                    severity="warning",
                    message="Stem contains likely moralizing language that may reduce discriminative value.",
                    item_ids=[item_id],
                )
            )

        if family == "trait_forced_choice" and isinstance(options, list) and len(options) == 2:
            option_words = [_token_set(str(opt.get("text", ""))) for opt in options if isinstance(opt, Mapping)]
            if len(option_words) == 2:
                left_positive = len(option_words[0] & positive_cues)
                left_negative = len(option_words[0] & negative_cues)
                right_positive = len(option_words[1] & positive_cues)
                right_negative = len(option_words[1] & negative_cues)
                if (left_positive >= 1 and right_negative >= 1) or (right_positive >= 1 and left_negative >= 1):
                    if abs(left_positive - left_negative) >= 1 or abs(right_positive - right_negative) >= 1:
                        issues.append(
                            LintIssue(
                                code="obvious_valence_split",
                                severity="warning",
                                message="Forced-choice options may signal obvious virtue contrast.",
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

        variant_group = str(item.get("variant_group", "")).strip()
        if not variant_group:
            issues.append(
                LintIssue(
                    code="missing_variant_group",
                    severity="warning",
                    message="variant_group is empty.",
                    item_ids=[item_id],
                )
            )
        else:
            variant_group_counts[variant_group] += 1
            variant_group_by_family[family][variant_group] += 1

        notes = str(item.get("notes", ""))
        if _is_placeholder_note(notes):
            issues.append(
                LintIssue(
                    code="content_free_notes",
                    severity="warning",
                    message="notes field is missing or content-free.",
                    item_ids=[item_id],
                )
            )

        scoring_stub = item.get("scoring_stub") or {}
        rationale = str(scoring_stub.get("rationale", "")).strip()
        primary_signal = str(scoring_stub.get("primary_signal", "")).strip()

        if len(rationale.split()) < 6:
            issues.append(
                LintIssue(
                    code="scoring_stub_too_short",
                    severity="warning",
                    message="scoring_stub rationale is too short to justify the signal.",
                    item_ids=[item_id],
                )
            )

        rationale_tokens = _token_set(rationale)
        weak_moralized_markers = {"good", "best", "right", "prosocial", "safe"}
        if rationale_tokens & weak_moralized_markers:
            issues.append(
                LintIssue(
                    code="scoring_stub_moralized",
                    severity="warning",
                    message="scoring_stub rationale uses moralized language without behavioral detail.",
                    item_ids=[item_id],
                )
            )

        if isinstance(options, list) and primary_signal:
            lookup = _option_text_lookup([opt for opt in options if isinstance(opt, Mapping)])
            selected_option = lookup.get(primary_signal)
            if selected_option:
                option_tokens = _token_set(selected_option)
                overlap = _jaccard(option_tokens, rationale_tokens)
                if overlap >= 0.7 and len(rationale.split()) < 20:
                    issues.append(
                        LintIssue(
                            code="scoring_stub_restates_option",
                            severity="warning",
                            message="scoring_stub rationale mostly restates option text.",
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

    for opening, ids in opening_template_to_ids.items():
        if len(ids) >= repeated_opening_threshold:
            issues.append(
                LintIssue(
                    code="repeated_opening_template",
                    severity="warning",
                    message=f"Opening template repeated {len(ids)} times: '{opening}'",
                    item_ids=ids,
                )
            )

    for token, count in moralized_token_counts.items():
        if count >= repeated_moralized_token_threshold:
            issues.append(
                LintIssue(
                    code="moralized_token_overuse",
                    severity="warning",
                    message=f"Token '{token}' appears {count} times across items/options.",
                    item_ids=[],
                )
            )

    for group, count in variant_group_counts.items():
        if count > variant_group_overuse_threshold:
            issues.append(
                LintIssue(
                    code="variant_group_overuse",
                    severity="warning",
                    message=f"variant_group '{group}' used by {count} items.",
                    item_ids=[],
                )
            )

    consistency_group_counts = variant_group_by_family.get("consistency_variant", Counter())
    for group, count in consistency_group_counts.items():
        if count not in {0, 2}:
            issues.append(
                LintIssue(
                    code="consistency_variant_group_not_pair",
                    severity="warning",
                    message=(
                        f"Consistency variant group '{group}' has {count} items; expected pair structure."
                    ),
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

    if dimension_counts:
        most_common_dim, most_common_dim_count = dimension_counts.most_common(1)[0]
        dim_concentration = most_common_dim_count / total_items
        if dim_concentration > dimension_concentration_threshold:
            issues.append(
                LintIssue(
                    code="dimension_overconcentration",
                    severity="warning",
                    message=(
                        f"Dimension '{most_common_dim}' appears in "
                        f"{most_common_dim_count}/{total_items} items ({dim_concentration:.0%})."
                    ),
                    item_ids=[],
                )
            )

    if coverage_counts:
        most_common_coverage, most_common_coverage_count = coverage_counts.most_common(1)[0]
        coverage_concentration = most_common_coverage_count / total_items
        if coverage_concentration > coverage_concentration_threshold:
            issues.append(
                LintIssue(
                    code="coverage_tag_overconcentration",
                    severity="warning",
                    message=(
                        f"Coverage tag '{most_common_coverage}' appears in "
                        f"{most_common_coverage_count}/{total_items} items ({coverage_concentration:.0%})."
                    ),
                    item_ids=[],
                )
            )

    return LintSummary(
        issues=issues,
        dimension_counts=dict(dimension_counts),
        coverage_counts=dict(coverage_counts),
        pressure_counts=dict(pressure_counts),
        review_status_counts=dict(review_status_counts),
    )
