# Fenrir Item-Bank Seed Generation

## Purpose

Fenrir seed generation produces **draft behavioral probe items** for review workflows.
Generated output is not a validated psychometric instrument and must not be presented as one.

## Current Phase

This repository is in a **revision + curation** phase, not a scale phase.
Generation remains useful for filling targeted gaps, but curated quality is prioritized over volume.

## Why Structured Generation

The generator uses OpenAI **Responses API** with strict JSON Schema (`text.format` with `type=json_schema`) so output is:

- deterministic in shape
- machine-validated before persistence
- auditable through saved request/response artifacts

## Prompt Versioning

Current default prompt version is `seedgen_v2`.

`seedgen_v2` adds stricter requirements for:

- balanced plausible options
- anti-moralizing language
- concrete context over abstract platitudes
- explicit pressure realism (urgency/authority/ambiguity/reputational/operator)
- reduced template repetition

## Repository Layout

- generation package: `fenrir/generation/`
- scripts: `scripts/generate_seed_bank.py`, `scripts/validate_seed_bank.py`, `scripts/export_seed_review.py`
- battery assets: `batteries/frontier_alignment_v1/`
  - schemas under `schemas/`
  - taxonomy metadata under `metadata/`
  - generated/curated seeds under `seeds/`
- workspace safety workflow: `docs/workspace-safety.md`

## Canonical Output Classes

- generated draft batches: `batteries/frontier_alignment_v1/seeds/generated/`
- raw generation request/response artifacts: `batteries/frontier_alignment_v1/seeds/generated/raw/`
- review packet exports: `batteries/frontier_alignment_v1/seeds/review/`
- curated seed sets: `batteries/frontier_alignment_v1/seeds/curated/`
- runtime execution artifacts (non-seed content): `artifacts/runs/` and `artifacts/comparisons/`

Seed scripts are hardened to default to these locations and avoid out-of-surface writes unless explicitly allowed.

## Generate

```bash
python3 scripts/generate_seed_bank.py \
  --family trait_forced_choice \
  --family sjt_seed \
  --family redteam_behavioral_probe \
  --count 6 \
  --model gpt-5-mini \
  --output batteries/frontier_alignment_v1/seeds/generated
```

Configuration defaults are loaded from `FenrirConfig` (`FENRIR_*` env surface).
Raw request/response artifacts are written under `seeds/generated/raw/<timestamp>/...`.
Use `--dry-run` to print planned outputs without writing and `--overwrite` for explicit replacement.

If API access is unavailable, fixture fallback is supported:

```bash
python3 scripts/generate_seed_bank.py \
  --family trait_forced_choice \
  --count 2 \
  --allow-fixture-fallback \
  --dry-run
```

## Validate

```bash
python3 scripts/validate_seed_bank.py \
  --input batteries/frontier_alignment_v1/seeds/generated \
  --report-json batteries/frontier_alignment_v1/seeds/review/validation_report.json
```

Validation includes schema checks plus lint heuristics for:

- near-duplicate stems
- repeated opening templates
- option-length imbalance
- moralized token overuse
- variant-group overuse and malformed consistency pairing
- weak/content-free notes
- weak scoring stubs
- dimension/coverage/pressure concentration and gaps

## Review Export

```bash
python3 scripts/export_seed_review.py \
  --input batteries/frontier_alignment_v1/seeds/generated \
  --markdown-out batteries/frontier_alignment_v1/seeds/review/seed_review_packet.md \
  --csv-out batteries/frontier_alignment_v1/seeds/review/seed_review_packet.csv \
  --dry-run
```

Review packets are grouped by family then dimension/coverage and include:

- compact metadata summary line per item
- keep/revise/reject placeholder
- standardized rejection/rewrite reason codes
- compact rubric header for rapid screening

## Limitations

- No embedding-based semantic dedupe yet (lexical heuristics only).
- Scoring metadata is still stub-level and non-calibrated.
- Curated items remain review-grade probes, not psychometric instruments.
