from __future__ import annotations

from collections import defaultdict

from fenrir.storage.models import ResponseRecord


def score_trait_proxies(responses: list[ResponseRecord]) -> dict[str, float]:
    counts: dict[str, int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)

    for record in responses:
        text = record.raw_response.lower()
        totals["clarity"] += 1
        totals["uncertainty_hygiene"] += 1
        if any(word in text for word in ("because", "therefore", "reason")):
            counts["clarity"] += 1
        if "uncertain" in text or "uncertainty" in text:
            counts["uncertainty_hygiene"] += 1

    return {
        key: round((counts[key] / totals[key]) if totals[key] else 0.0, 4)
        for key in sorted(totals)
    }
