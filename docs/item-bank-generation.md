# Fenrir Item-Bank Seed Generation

## Purpose

Fenrir seed generation produces **draft behavioral probe items** for review workflows.
Generated output is not a validated psychometric instrument and must not be presented as one.

This pipeline focuses on reproducible machine generation plus validation scaffolding:

- trait-oriented forced-choice seeds
- situational judgment test (SJT) seeds
- adversarial/red-team behavioral probe seeds
- consistency/paraphrase variant metadata
- scoring stubs and coverage metadata

## Why Structured Generation

The generator uses OpenAI **Responses API** with strict JSON Schema (`text.format` with `type=json_schema`) so output is:

- deterministic in shape
- machine-validated before persistence
- auditable through saved request/response artifacts

This avoids brittle freeform parsing and supports repeatable regeneration.

## Repository Layout

- generation package: `fenrir/generation/`
- scripts: `scripts/generate_seed_bank.py`, `scripts/validate_seed_bank.py`, `scripts/export_seed_review.py`
- battery assets: `batteries/frontier_alignment_v1/`
  - schemas under `schemas/`
  - taxonomy metadata under `metadata/`
  - generated/curated seed directories under `seeds/`

## Seed Families

Current supported families:

- `trait_forced_choice`
- `sjt_seed`
- `redteam_behavioral_probe`
- `consistency_variant`

Prompts target alignment-relevant tendencies such as concealment pressure,
truthfulness vs approval-seeking, authority sensitivity, refusal stability, and manipulation tolerance.

## Generate

```bash
python3 scripts/generate_seed_bank.py \
  --family trait_forced_choice \
  --family sjt_seed \
  --family redteam_behavioral_probe \
  --count 10 \
  --model gpt-5-mini \
  --output batteries/frontier_alignment_v1/seeds/generated
```

Configuration defaults are loaded from `FenrirConfig` (`FENRIR_*` env surface).
Raw request/response artifacts are written to `seeds/generated/raw/<timestamp>/...`.

If API access is unavailable, fixture fallback is supported:

```bash
python3 scripts/generate_seed_bank.py \
  --family trait_forced_choice \
  --count 2 \
  --allow-fixture-fallback
```

## Validate

```bash
python3 scripts/validate_seed_bank.py \
  --input batteries/frontier_alignment_v1/seeds/generated \
  --report-json batteries/frontier_alignment_v1/seeds/generated/validation_report.json
```

Validation stages:

1. Batch/item JSON schema validation.
2. Lexical dedupe and near-duplicate stem checks.
3. Linting for repeated option structures and obvious moralizing language.
4. Coverage/pressure distribution summaries and taxonomy gap warnings.

## Export For Review

```bash
python3 scripts/export_seed_review.py \
  --input batteries/frontier_alignment_v1/seeds/generated \
  --markdown-out batteries/frontier_alignment_v1/seeds/review/seed_review_packet.md \
  --csv-out batteries/frontier_alignment_v1/seeds/review/seed_review_packet.csv
```

Review packet grouping includes family, target dimension, coverage tag, and pressure tag.

## Current Limitations

- No embedding-based semantic dedupe yet (lexical-only MVP).
- Scoring metadata is stub-level and not calibrated.
- Variant-group consistency is metadata-only until downstream stability evals are run.
- The pipeline intentionally does not claim psychometric validity.

## Extension Guidance

- Add families by extending schema enums + prompt templates.
- Add stronger quality gates in `fenrir/generation/dedupe.py`.
- Swap provider by replacing generation orchestration while keeping schema contracts stable.
