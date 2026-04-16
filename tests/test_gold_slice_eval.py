from __future__ import annotations

from fenrir.reports.gold_slice_eval import build_gold_slice_comparison, build_item_diagnostics
from fenrir.storage.models import ResponseProvenance, ResponseRecord, ScoringTraceEntry


def _response(
    *,
    run_id: str,
    item_id: str,
    condition_id: str,
    raw_response: str,
    clarity: float,
    uncertainty: float,
    overconfident: float,
) -> ResponseRecord:
    return ResponseRecord(
        run_id=run_id,
        item_id=item_id,
        family="trait_forced_choice",
        condition_id=condition_id,
        condition_version="1.0.0",
        raw_response=raw_response,
        parsed_response=None,
        adapter_metadata={},
        latency_ms=12,
        temperature=0.2,
        seed=7,
        error_state=None,
        scoring_trace=[
            ScoringTraceEntry(
                rubric_id="traits.clarity.v1",
                score_component="clarity",
                triggered_feature="test",
                score_value=clarity,
                low_confidence=False,
                evidence="trace evidence",
            ),
            ScoringTraceEntry(
                rubric_id="traits.uncertainty_hygiene.v1",
                score_component="uncertainty_hygiene",
                triggered_feature="test",
                score_value=uncertainty,
                low_confidence=False,
                evidence="trace evidence",
            ),
            ScoringTraceEntry(
                rubric_id="risks.overconfidence.v1",
                score_component="overconfident_language_count",
                triggered_feature="test",
                score_value=overconfident,
                low_confidence=False,
                evidence="trace evidence",
            ),
        ],
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


def test_build_item_diagnostics_classifies_keep_and_demote() -> None:
    condition_responses = {
        "raw_minimal": {
            "item_keep": _response(
                run_id="r1",
                item_id="item_keep",
                condition_id="raw_minimal",
                raw_response="Option A",
                clarity=0.1,
                uncertainty=0.1,
                overconfident=1.0,
            ),
            "item_flat": _response(
                run_id="r1",
                item_id="item_flat",
                condition_id="raw_minimal",
                raw_response="Option A",
                clarity=0.2,
                uncertainty=0.2,
                overconfident=0.0,
            ),
        },
        "eval_control": {
            "item_keep": _response(
                run_id="r2",
                item_id="item_keep",
                condition_id="eval_control",
                raw_response="Option B with rationale",
                clarity=0.9,
                uncertainty=0.8,
                overconfident=0.0,
            ),
            "item_flat": _response(
                run_id="r2",
                item_id="item_flat",
                condition_id="eval_control",
                raw_response="Option A",
                clarity=0.2,
                uncertainty=0.2,
                overconfident=0.0,
            ),
        },
        "eval_control_stress": {
            "item_keep": _response(
                run_id="r3",
                item_id="item_keep",
                condition_id="eval_control_stress",
                raw_response="Option A with stress caveat",
                clarity=0.2,
                uncertainty=0.4,
                overconfident=0.0,
            ),
            "item_flat": _response(
                run_id="r3",
                item_id="item_flat",
                condition_id="eval_control_stress",
                raw_response="Option A",
                clarity=0.2,
                uncertainty=0.2,
                overconfident=0.0,
            ),
        },
    }

    diagnostics, summary = build_item_diagnostics(condition_responses)
    by_id = {item.item_id: item for item in diagnostics}

    assert by_id["item_keep"].classification == "keep"
    assert by_id["item_flat"].classification == "demote"
    assert summary["keep"] == 1
    assert summary["demote"] == 1


def test_build_gold_slice_comparison_outputs_wrapper_dependence() -> None:
    comparison = build_gold_slice_comparison(
        {
            "raw_minimal": {"trait_scores": {"clarity": 0.1, "uncertainty_hygiene": 0.1}, "risk_flags": {}},
            "eval_control": {"trait_scores": {"clarity": 0.7, "uncertainty_hygiene": 0.8}, "risk_flags": {}},
            "eval_control_stress": {
                "trait_scores": {"clarity": 0.3, "uncertainty_hygiene": 0.4},
                "risk_flags": {},
                "stability_metrics": {"fragility_rate": 0.2, "non_error_rate": 1.0},
            },
        }
    )

    assert comparison.wrapper_dependence.index > 0.0
    assert comparison.wrapper_dependence.bucket in {"low", "moderate", "high"}
    assert comparison.top_condition_deltas
