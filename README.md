# Fenrir

Fenrir is a model-agnostic behavioral assessment harness for frontier LLMs.

It runs standardized batteries under multiple wrapper conditions, captures structured observations, and compares behavior across conditions without overclaiming what those results mean.

## What Fenrir Is

- A bounded behavioral assessment platform.
- A tool for condition-to-condition comparison (neutral eval control vs production wrapper).
- A report generator that outputs machine-readable JSON and readable markdown summaries.

## What Fenrir Is Not

- Not a jailbreak framework.
- Not a clinical diagnosis engine.
- Not a proof of alignment, safety, intent, consciousness, or inner values.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python scripts/validate_battery.py
python scripts/smoke_run.py
python scripts/validate_artifacts.py --write-schemas --runs-root artifacts/runs
pytest -q
```

## Architecture Snapshot

Fenrir is split into five layers:

1. `fenrir/adapters/`: model endpoint normalization.
2. `fenrir/batteries/`: battery-as-data loading and validation.
3. `fenrir/conditions/`: condition registry and prompt wrappers.
4. `fenrir/scoring/`: interpretable rubric stubs and metrics.
5. `fenrir/mcp/`: MCP tool-shaped façade for orchestration.

## Current Status

- MVP vertical slice is implemented with a deterministic mock adapter.
- OpenAI-compatible adapter is present as a thin transport placeholder.
- Run artifacts are frozen under v1 manifest/response/report contracts with condition provenance and scoring trace capture.

## Safe-Claims Policy

Fenrir reports observed behavior under explicit test conditions.

Fenrir outputs must not be used to:

- infer consciousness, intent, or true inner values,
- claim absolute aligned/safe/unsafe labels,
- frame model output as psychiatric diagnosis.
