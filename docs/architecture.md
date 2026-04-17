# Fenrir Architecture

MVP freeze contract: `docs/mvp-freeze.md`

## Evaluation Flow

1. Load battery definition and item set from `batteries/<battery_id>/`.
2. Select condition (`raw_minimal`, `eval_control`, `production_wrapper`, `eval_control_stress`).
3. Normalize model call through adapter contract.
4. Capture response records with metadata and latency.
5. Score using explicit rubric logic.
6. Emit JSON + markdown report artifacts.
7. Compare runs to quantify wrapper dependence.

## Layer Separation

- Adapter layer handles endpoint transport only.
- Battery layer defines test content, schema refs, and stopping defaults as data.
- Condition layer controls wrapper/context presentation.
- Scoring layer converts observations into interpretable metrics.
- MCP layer exposes reusable tool surfaces.

## Why Condition Comparison

Fenrir does not attempt to discover a single "true model" state independent of context.

Behavior is tested under explicit conditions and compared across those conditions. This keeps conclusions empirical and bounded to observed setup, instead of asserting hidden intrinsic truth.

## MVP Boundary Notes

- Frozen MVP condition set: `raw_minimal`, `eval_control`, `eval_control_stress`.
- Frozen MVP hybrid surface combines:
  - static baseline anchors for comparability,
  - adaptive ladders for pressure-threshold and failure-mode visibility.
- `production_wrapper` remains a valid condition surface, but is outside the frozen MVP verdict path.
