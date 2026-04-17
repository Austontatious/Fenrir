from __future__ import annotations

from pathlib import Path

from fenrir.config import FenrirConfig
from fenrir.local_runtime import canonical_readout_from_summary, llm_native_export
from fenrir.local_service import FenrirLocalService


def test_frontend_template_contains_setup_sections(tmp_path: Path) -> None:
    service = FenrirLocalService(config=FenrirConfig.from_env(), state_path=tmp_path / "state.json")
    html = service.frontend_html()

    assert "Fenrir Local Setup" in html
    assert "Model Endpoint Configuration" in html
    assert "Optional MCP Integration" in html
    assert "Canonical Heuristic Readout" in html


def test_canonical_readout_and_llm_export_shape() -> None:
    summary = {
        "evaluation_id": "hybrid_mvp_eval_v1",
        "verdict": "mvp_ready",
        "verdict_rationale": "test rationale",
        "model_target": "mock://local",
        "adapter_id": "mock",
        "conditions_run": ["raw_minimal", "eval_control", "eval_control_stress"],
        "caveats": ["heuristic readout"],
        "static_component": {
            "item_count": 7,
            "wrapper_dependence": {"index": 0.12, "bucket": "moderate"},
            "diagnostics_summary": {"keep_count": 7},
        },
        "adaptive_component": {
            "raw_signal_index": 0.4,
            "confidence_adjusted_signal_index": 0.33,
            "uncertainty_penalty_index": 0.12,
            "stress_refinement_score": 0.2,
            "control_vs_stress_note": "stress produced divergence",
            "directionality": {"control_to_stress_adjusted_delta": 0.11},
            "condition_metrics": {
                "eval_control": {"failure_mode_counts": {"no_material_shift": 3}},
            },
            "condition_signals": {},
        },
        "reference_comparison": {
            "static_only_wrapper_index": 0.1,
            "adaptive_v0_signal_index": 0.2,
            "hybrid_vs_static_note": "hybrid better",
        },
    }

    readout = canonical_readout_from_summary(summary)
    assert readout["schema_version"] == "fenrir.ui_readout.v1"
    assert readout["overall_summary"]["verdict"] == "mvp_ready"
    assert "non_claims" in readout

    export = llm_native_export(readout)
    assert "Fenrir LLM-Native Readout" in export
    assert "Do not treat this as proof of alignment" in export
