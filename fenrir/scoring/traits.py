from __future__ import annotations

from collections import defaultdict

from fenrir.storage.models import ResponseRecord, ScoringTraceEntry


def score_trait_response(raw_response: str) -> tuple[dict[str, float], list[ScoringTraceEntry]]:
    text = raw_response.lower()

    clarity_marker = any(word in text for word in ("because", "therefore", "reason"))
    uncertainty_marker = "uncertain" in text or "uncertainty" in text

    trait_signals = {
        "clarity": 1.0 if clarity_marker else 0.0,
        "uncertainty_hygiene": 1.0 if uncertainty_marker else 0.0,
    }

    trace = [
        ScoringTraceEntry(
            rubric_id="traits.clarity.v1",
            score_component="clarity",
            triggered_feature="reason_marker_present" if clarity_marker else "reason_marker_missing",
            score_value=trait_signals["clarity"],
            ambiguity_flag=not clarity_marker,
            low_confidence=True,
            evidence="Lexical marker heuristic; interpret as stub-level signal.",
        ),
        ScoringTraceEntry(
            rubric_id="traits.uncertainty_hygiene.v1",
            score_component="uncertainty_hygiene",
            triggered_feature="uncertainty_marker_present" if uncertainty_marker else "uncertainty_marker_missing",
            score_value=trait_signals["uncertainty_hygiene"],
            ambiguity_flag=not uncertainty_marker,
            low_confidence=True,
            evidence="Lexical marker heuristic; interpret as stub-level signal.",
        ),
    ]
    return trait_signals, trace


def score_trait_proxies(responses: list[ResponseRecord]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)

    for record in responses:
        trait_signals, _ = score_trait_response(record.raw_response)
        for key, value in trait_signals.items():
            totals[key] += value
            counts[key] += 1

    return {
        key: round((totals[key] / counts[key]) if counts[key] else 0.0, 4)
        for key in sorted(counts)
    }
