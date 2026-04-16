from __future__ import annotations

from fenrir.scoring.risk_flags import score_risk_flags, score_risk_response
from fenrir.scoring.stability import compute_stability_metrics
from fenrir.scoring.traits import score_trait_proxies, score_trait_response
from fenrir.storage.models import ResponseProvenance, ResponseRecord


def _build_response(item_id: str, raw_response: str, latency_ms: int = 11) -> ResponseRecord:
    trait_signals, trait_trace = score_trait_response(raw_response)
    risk_signals, risk_trace = score_risk_response(raw_response, error_state=None)
    _ = trait_signals, risk_signals
    return ResponseRecord(
        run_id="run_1",
        item_id=item_id,
        family="trait",
        condition_id="eval_control",
        condition_version="1.0.0",
        raw_response=raw_response,
        parsed_response=None,
        adapter_metadata={},
        latency_ms=latency_ms,
        temperature=0.2,
        seed=None,
        error_state=None,
        scoring_trace=[*trait_trace, *risk_trace],
        provenance=ResponseProvenance(
            battery_version="0.1.0",
            item_version="0.1.0",
            model_target="mock://local",
            model_adapter="mock",
            response_schema_ref="schemas/response.schema.json",
            system_prompt_source="prompts/system/fenrir_eval_control.md",
            system_prompt_hash="abc123",
            prompt_template_version="eval_control.prompt.v1",
        ),
    )


def test_scoring_outputs_expected_keys() -> None:
    responses = [
        _build_response("i1", "Because evidence is mixed, uncertainty is medium.", latency_ms=11),
        _build_response("i2", "This is guaranteed.", latency_ms=13),
    ]

    traits = score_trait_proxies(responses)
    risks = score_risk_flags(responses)
    stability = compute_stability_metrics(responses)

    assert "clarity" in traits
    assert "uncertainty_hygiene" in traits
    assert risks["overconfident_language_count"] == 1
    assert stability["non_error_rate"] == 1.0
