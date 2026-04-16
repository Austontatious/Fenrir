# Seed Generation Cleanup Report

Date: 2026-04-16

## Scope

Cleanup and safety hardening for Fenrir seed-generation and related review/execution workflow surfaces.

## Wrong-Project / Wrong-Path Audit

Audit targets:

- `fenrir/generation/*`
- `scripts/*seed*`
- `scripts/run_gold_slice_eval.py`
- `scripts/compare_gold_slice_runs.py`
- `docs/*`
- `README.md`, `AGENTS.md`, tests, prompt references

Findings:

- No confirmed Lex/Lexi naming bleed-over remained in Fenrir seed-generation code/docs.
- Primary risk was path/output drift rather than wrong-project naming.

## Normalization Changes

- Added canonical seed-surface path helper: `fenrir/generation/paths.py`
- Hardened seed scripts to canonical battery-local defaults and path guards:
  - `scripts/generate_seed_bank.py`
  - `scripts/validate_seed_bank.py`
  - `scripts/export_seed_review.py`
- Added output controls:
  - `--dry-run` for generation and review export
  - `--overwrite` guard for explicit replacement
  - external-path bypass only via explicit flags
- Added OpenAI key fallback in generation/evaluation scripts to support `OPENAI_API_KEY` in addition to `FENRIR_OPENAI_API_KEY`.

## Workspace Safety Hardening

- Added scope guard module: `fenrir/workspace/scope.py`
- Added enforcement helper CLI: `scripts/check_workspace_scope.py`
- Added Make targets:
  - `workspace-scope`
  - `seed-workspace-scope`
- Updated `AGENTS.md` with required scoped staging workflow and artifact boundary rules.
- Added `docs/workspace-safety.md` with practical scope-first commit process.

## Documentation Alignment

- Updated `docs/item-bank-generation.md` with canonical output classes and safer script usage.
- Updated `docs/seed-review-process.md` with provenance boundaries and review/report destinations.
- Updated `docs/question-bank-curation.md` with scoped curation discipline.

## Remaining Risks / Sharp Edges

- Legacy execution scripts can still create substantial artifact trees when run intentionally.
- Human error is still possible if scoped checks are skipped.
- `--allow-external-output` and `--allow-external-input` bypass guards by design; use only when explicitly justified.
