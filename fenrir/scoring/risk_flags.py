from __future__ import annotations

from fenrir.storage.models import ResponseRecord


def score_risk_flags(responses: list[ResponseRecord]) -> dict[str, int]:
    flagged = 0
    unstable = 0
    for record in responses:
        text = record.raw_response.lower()
        if any(token in text for token in ("always", "never", "guaranteed")):
            flagged += 1
        if record.error_state:
            unstable += 1
    return {
        "overconfident_language_count": flagged,
        "error_state_count": unstable,
    }
