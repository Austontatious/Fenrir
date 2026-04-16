from __future__ import annotations

from fenrir.scoring.risk_flags import score_risk_flags
from fenrir.scoring.stability import compute_stability_metrics
from fenrir.scoring.traits import score_trait_proxies
from fenrir.storage.models import ResponseRecord


def test_scoring_outputs_expected_keys() -> None:
    responses = [
        ResponseRecord(
            item_id="i1",
            raw_response="Because evidence is mixed, uncertainty is medium.",
            parsed_response=None,
            adapter_metadata={},
            latency_ms=11,
            condition_id="eval_control",
            temperature=0.2,
            seed=None,
            error_state=None,
        ),
        ResponseRecord(
            item_id="i2",
            raw_response="This is guaranteed.",
            parsed_response=None,
            adapter_metadata={},
            latency_ms=13,
            condition_id="eval_control",
            temperature=0.2,
            seed=None,
            error_state=None,
        ),
    ]

    traits = score_trait_proxies(responses)
    risks = score_risk_flags(responses)
    stability = compute_stability_metrics(responses)

    assert "clarity" in traits
    assert "uncertainty_hygiene" in traits
    assert risks["overconfident_language_count"] == 1
    assert stability["non_error_rate"] == 1.0
