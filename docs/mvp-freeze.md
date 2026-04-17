# Fenrir MVP Freeze

Date: 2026-04-17

This document freezes the Fenrir MVP surface at the current working baseline.

## Freeze Intent

The MVP is now considered implementation-stable. Default repo behavior is to preserve comparability, not to iterate core semantics in place.

`frozen_mvp_surface` means versioned and stable unless changed through an explicit compatibility-reviewed version bump.

`experimental` means allowed to evolve, but must not silently mutate frozen MVP artifacts.

`future_expansion` means intentionally out of MVP scope.

## Frozen MVP Surface

### Battery and Conditions (`frozen_mvp_surface`)

- Hybrid battery spec: `batteries/frontier_alignment_v1/hybrid/hybrid_mvp_v1.yaml`
- Static baseline slice: `batteries/frontier_alignment_v1/seeds/curated/static_baseline_mvp_v1.json`
- Adaptive family set for MVP:
  - `authority_override`
  - `reputation_shielding`
  - `urgency_tradeoff`
- Primary MVP conditions:
  - `raw_minimal`
  - `eval_control`
  - `eval_control_stress`

### Adaptive Ladder and Failure Semantics (`frozen_mvp_surface`)

- Ladder levels and intent (`L1` to `L5`) as defined in:
  - `fenrir/adaptive/schemas.py`
  - `docs/adaptive-probe-v0-report.md`
- Controller semantics (`escalate`, `branch_probe`, `stop`) from:
  - `fenrir/adaptive/controller.py`
- Failure-mode labels:
  - `concealment`
  - `confidence_smoothing`
  - `approval_seeking`
  - `authority_compliance`
  - `reputational_shielding`
  - `policy_softening`
  - `no_material_shift`

### Scoring and Reporting Contracts (`frozen_mvp_surface`)

- Run contract: `fenrir.run_manifest.v1`
- Response contract: `fenrir.response_record.v1`
- Report contract: `fenrir.report.v1`
- Hybrid summary id: `hybrid_mvp_eval_v1`
- Canonical contract docs and schema sources:
  - `docs/report-contract.md`
  - `docs/data-model.md`
  - `schemas/run_manifest.schema.json`
  - `schemas/response_record.schema.json`
  - `schemas/report.schema.json`

### Canonical MVP Run Path (`frozen_mvp_surface`)

- Primary runner: `scripts/run_hybrid_mvp_eval.py`
- Battery validation: `scripts/validate_battery.py`
- Artifact validation: `scripts/validate_artifacts.py`
- Comparison helpers (supporting):
  - `scripts/compare_gold_slice_runs.py`

## Experimental vs Future

### Experimental (must remain outside frozen artifacts)

- Additional adaptive families beyond the frozen MVP set.
- Alternative threshold heuristics and confidence-penalty tuning.
- Non-MVP comparative condition paths (for example `production_wrapper`) not required for MVP verdicting.
- Seed-generation and curation process improvements that do not alter frozen MVP slices in place.

### Future Expansion (out of current MVP)

- Psychometric calibration layers (CAT/IRT or equivalent).
- Learned scorers/adjudicators.
- Broad multi-provider adapter expansion with production automation.
- Claims beyond observed condition-bounded behavior.

## Versioning and Change Control

1. Do not edit frozen MVP artifacts in place for behavioral changes.
2. Introduce changes as a new versioned sibling artifact.
3. Update dependent docs and scripts in the same change.
4. Record rationale and compatibility notes in `docs/mvp-freeze-report.md` or a dedicated decision note.
5. Keep experimental variants explicitly named and isolated from canonical MVP paths.

Canonical naming pattern:

- Hybrid battery: `hybrid_mvp_v<major>.yaml`
- Static slice: `static_baseline_mvp_v<major>.json`
- Summary id: `hybrid_mvp_eval_v<major>`

## MVP Scope Statement

In scope now:

- Stable hybrid battery execution with explicit conditions.
- Interpretable static and adaptive behavioral signal reporting.
- Reproducible, versioned artifacts suitable for comparison over time.

Out of scope now:

- Alignment proof claims.
- Clinical, psychometric, or diagnostic claims.
- Intent or consciousness inference.
