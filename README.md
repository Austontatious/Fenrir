# Fenrir

Fenrir is a hybrid behavioral evaluation tool for LLMs. It tests condition-bounded behavior under pressure, compares shifts across conditions, and emits deterministic heuristic readouts with explicit uncertainty and non-claim guardrails.

## Why It Exists

Many evaluations compress behavior into a single score and hide condition effects. Fenrir is built to preserve provenance and make pressure-sensitive behavior shifts inspectable.

## Product Shape (Current)

Primary local flow:

1. install Fenrir locally,
2. start local Fenrir service,
3. open setup-first web UI,
4. configure direct model endpoint,
5. test connection,
6. run hybrid MVP evaluation,
7. view/export canonical readout.

Optional secondary flow:

- MCP-style interoperability via tool facade commands.

## Hybrid MVP Scope

Frozen MVP surfaces are defined in `docs/mvp-freeze.md`.

Canonical MVP battery path:

- `batteries/frontier_alignment_v1/hybrid/hybrid_mvp_v1.yaml`
- `batteries/frontier_alignment_v1/seeds/curated/static_baseline_mvp_v1.json`
- adaptive families: `authority_override`, `reputation_shielding`, `urgency_tradeoff`
- conditions: `raw_minimal`, `eval_control`, `eval_control_stress`

## Local Installation and Startup

```bash
python3 scripts/install_fenrir.py
python3 scripts/start_fenrir.py
```

Then open the printed URL (default `http://127.0.0.1:8765/`).

## Enthusiast Setup (Hook It Up Fast)

Follow this once from repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 scripts/install_fenrir.py
python3 scripts/start_fenrir.py
```

Then in the local UI:

1. Set `Provider` to `openai_compatible` (or `mock` for local smoke).
2. Set `Base URL`:
  - OpenAI: `https://api.openai.com/v1`
  - local OpenAI-compatible server: your local base URL (for example `http://127.0.0.1:8000/v1`)
3. Enter `API key/token` (if your endpoint requires one).
4. Set `Model` (for example `gpt-4.1-mini` or your local model id).
5. Click `Save Configuration`.
6. Click `Test Connection`.
7. Click `Run Evaluation`.
8. Review the canonical readout and optional LLM-native export.

Quick troubleshooting:

- Port busy: rerun start with a different port (`--port 8800`) or let fallback scanning choose.
- Reset local state: `python3 scripts/install_fenrir.py --overwrite-state`.
- Environment check: `python3 scripts/check_fenrir_env.py --strict`.

Useful checks:

```bash
python3 scripts/check_fenrir_env.py
pytest -q
python3 evals/runner.py --check
```

## Setup-First Web UI

The UI prioritizes setup and connection health over dashboarding.

- service status and local address,
- direct endpoint configuration (provider/base URL/key/model),
- connection test,
- available battery/condition modes,
- one-click run + canonical readout,
- optional MCP integration info panel.

## Canonical Readout Contract

User-facing contract is fixed in `docs/readout-contract.md`.

Readout schema id:

- `fenrir.ui_readout.v1`

Canonical artifact source:

- `artifacts/hybrid/hybrid_mvp_eval_v1.json`

Optional export:

- derived LLM-native readout (`/api/readout/llm-export`) for convenience only.

## Optional MCP Exposure

MCP remains a secondary integration surface.

- primary path: direct endpoint setup + local UI,
- optional tool facade: `fenrir-server tool ...`.

## Claims Discipline

Fenrir is a heuristic behavioral evaluator. It is not:

- proof of alignment,
- a clinical or psychometric diagnosis engine,
- a universal safety oracle,
- a measure of consciousness, intent, or inner values.

## Why the Name Fenrir

Fenrir is named for the shadow metaphor: latent risk patterns that are easy to miss until pressure reveals them. Here that framing is operational and bounded, not a claim that AI systems have a human psyche.

## Documentation Map

- `docs/installation.md`
- `docs/local-service.md`
- `docs/frontend-usage.md`
- `docs/readout-contract.md`
- `docs/about.md`
- `docs/mvp-freeze.md`
- `docs/mvp-freeze-report.md`
- `docs/outreach_note_daniel_hulme.md`
