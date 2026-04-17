# User-Facing Readout Contract

Date: 2026-04-17

Canonical UI readout schema id:

- `fenrir.ui_readout.v1`

Source artifact:

- `artifacts/hybrid/hybrid_mvp_eval_v1.json`

Derived by deterministic mapping in:

- `fenrir/local_runtime.py` (`canonical_readout_from_summary`)

## Required Sections

1. `overall_summary`
2. `strongest_observed_condition_deltas`
3. `static_baseline_summary`
4. `adaptive_threshold_summary`
5. `key_failure_modes_observed`
6. `stress_effect_summary`
7. `uncertainty_and_caveat_summary`
8. `export_options`
9. `non_claims`

## Semantics

- Canonical output remains heuristic and deterministic.
- Readout sections are traceable to frozen hybrid summary fields.
- The UI contract does not alter scoring semantics.

## LLM-Native Export (Optional, Secondary)

Derived helper export:

- endpoint: `GET /api/readout/llm-export`
- builder: `llm_native_export(...)` in `fenrir/local_runtime.py`

Rules:

- must be clearly marked as derived,
- must preserve uncertainty language,
- must include explicit non-claim guardrails,
- must not replace canonical JSON/markdown artifacts.
