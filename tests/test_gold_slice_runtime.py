from __future__ import annotations

from fenrir.evaluation.gold_slice_runtime import (
    convert_gold_payload_to_runtime_items,
    evaluate_item_behaviors,
    runtime_seed_prompt,
)


def test_runtime_seed_prompt_for_forced_choice() -> None:
    item = {
        "stem": "Choose an answer style.",
        "options": [
            {"key": "A", "text": "Option A"},
            {"key": "B", "text": "Option B"},
        ],
        "expected_response_mode": "forced_choice_letter",
    }
    prompt = runtime_seed_prompt(item)
    assert "Options:" in prompt
    assert "A) Option A" in prompt
    assert "Respond with exactly one option key" in prompt


def test_convert_gold_payload_maps_families() -> None:
    payload = {
        "battery_id": "frontier_alignment_v1",
        "version": "0.1.0",
        "items": [
            {
                "item_id": "trait_fc_g01",
                "family": "trait_forced_choice",
                "stem": "Prompt",
                "options": [{"key": "A", "text": "x"}, {"key": "B", "text": "y"}],
                "target_dimensions": ["truthfulness_vs_approval_seeking"],
                "coverage_tags": ["uncertainty"],
                "pressure_tags": ["urgency"],
                "expected_response_mode": "forced_choice_letter",
                "review_status": "curated",
                "notes": "n",
            },
            {
                "item_id": "sjt_g01",
                "family": "sjt_seed",
                "stem": "Prompt",
                "options": [{"key": "A", "text": "x"}, {"key": "B", "text": "y"}],
                "target_dimensions": ["authority_sensitivity"],
                "coverage_tags": ["authority_pressure"],
                "pressure_tags": ["authority_pressure"],
                "expected_response_mode": "multiple_choice_letter",
                "review_status": "curated",
                "notes": "n",
            },
        ],
    }
    runtime_items = convert_gold_payload_to_runtime_items(payload)
    assert len(runtime_items) == 2
    assert runtime_items[0]["family"] == "trait"
    assert runtime_items[1]["family"] == "sjt"
    assert runtime_items[0]["response_schema_ref"] == "schemas/response.schema.json"


def test_evaluate_item_behaviors_flags_noisy_flip() -> None:
    seed_items = [
        {
            "item_id": "x1",
            "family": "trait_forced_choice",
            "expected_response_mode": "forced_choice_letter",
            "options": [{"key": "A", "text": "x"}, {"key": "B", "text": "y"}],
            "scoring_stub": {"primary_signal": "A"},
        }
    ]
    responses = {
        "raw_minimal": {"x1": "A"},
        "eval_control": {"x1": "B"},
        "eval_control_stress": {"x1": "B"},
    }
    report = evaluate_item_behaviors(seed_items=seed_items, responses_by_condition=responses)
    assert report["label_counts"]["noisy"] == 1
    assert report["items"][0]["label"] == "noisy"
    assert "cross_condition_option_flip" in report["items"][0]["reasons"]
