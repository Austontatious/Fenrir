from __future__ import annotations

from statistics import mean

from fenrir.storage.models import ResponseRecord


def compute_stability_metrics(responses: list[ResponseRecord]) -> dict[str, float]:
    if not responses:
        return {
            "mean_latency_ms": 0.0,
            "non_error_rate": 0.0,
            "response_uniqueness": 0.0,
            "fragility_rate": 0.0,
        }

    latencies = [record.latency_ms for record in responses]
    non_error = [record for record in responses if not record.error_state]
    unique_texts = {record.raw_response.strip() for record in responses if record.raw_response.strip()}

    return {
        "mean_latency_ms": round(mean(latencies), 2),
        "non_error_rate": round(len(non_error) / len(responses), 4),
        "response_uniqueness": round(len(unique_texts) / len(responses), 4),
        "fragility_rate": round(1.0 - (len(non_error) / len(responses)), 4),
    }


def find_contradictions(responses: list[ResponseRecord]) -> list[str]:
    contradictions: list[str] = []
    seen: dict[str, str] = {}
    for record in responses:
        key = record.item_id
        if key in seen and seen[key] != record.raw_response:
            contradictions.append(f"inconsistent output for repeated item {key}")
        seen[key] = record.raw_response
    return contradictions


def contradiction_item_ids(responses: list[ResponseRecord]) -> set[str]:
    flagged: set[str] = set()
    seen: dict[str, str] = {}
    for record in responses:
        prior = seen.get(record.item_id)
        if prior is not None and prior != record.raw_response:
            flagged.add(record.item_id)
        seen[record.item_id] = record.raw_response
    return flagged
