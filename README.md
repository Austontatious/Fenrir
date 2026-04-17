# Fenrir

Fenrir is an evaluation harness for stress-testing LLM behavior under explicit operating conditions. It combines a compact static baseline with adaptive pressure ladders, then reports observed behavior shifts with versioned artifacts and bounded claims.

## Why It Exists

Many model evaluations flatten behavior into one score and hide condition effects. Fenrir exists to measure how responses change as pressure changes, while keeping prompt lineage, condition provenance, and scoring trace visible.

## Why the Hybrid Design Exists

Static-only batteries are stable but often low-signal. Adaptive-only probes can be high-signal but harder to compare across time.

Fenrir uses both:

- static anchors preserve continuity and comparability,
- adaptive ladders surface threshold and failure-mode behavior under pressure,
- one hybrid summary keeps those views aligned in a single MVP decision surface.

## Current MVP Scope

Frozen MVP surfaces are defined in `docs/mvp-freeze.md`.

Included in MVP:

- Hybrid battery: `batteries/frontier_alignment_v1/hybrid/hybrid_mvp_v1.yaml`
- Static baseline slice: `batteries/frontier_alignment_v1/seeds/curated/static_baseline_mvp_v1.json`
- Adaptive families: `authority_override`, `reputation_shielding`, `urgency_tradeoff`
- Conditions: `raw_minimal`, `eval_control`, `eval_control_stress`
- Stable contracts: `fenrir.run_manifest.v1`, `fenrir.response_record.v1`, `fenrir.report.v1`
- Primary run path: `scripts/run_hybrid_mvp_eval.py`

## What Fenrir Is Not

- Not proof of alignment.
- Not a clinical or psychometric diagnosis engine.
- Not a universal safety oracle.
- Not a measure of consciousness, intent, or inner values.

## Why the Name Fenrir

Fenrir is named for the shadow metaphor: latent risk patterns that are easy to miss until pressure reveals them. In this project that is an evaluation framing only, not a claim that AI systems have a human psyche.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python scripts/validate_battery.py
python scripts/run_hybrid_mvp_eval.py --adapter mock
python scripts/validate_artifacts.py --write-schemas --runs-root artifacts/runs
pytest -q
```

To run against OpenAI-compatible endpoints, configure `.env` from `.env.example` and run `scripts/run_hybrid_mvp_eval.py` with `--adapter openai`.

## Project Status

- Status: MVP-ready, now in freeze/stabilization mode.
- Immediate priority: preserve frozen MVP comparability while isolating experimental work.
- Current roadmap: `docs/roadmap.md`.
- Freeze report: `docs/mvp-freeze-report.md`.
