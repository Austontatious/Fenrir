# Report Contract

## Purpose

Fenrir run artifacts are intended to be durable, auditable, and comparable over time.

The stable contract in this phase is:

- `RunManifest` (`fenrir.run_manifest.v1`)
- `ResponseRecord` (`fenrir.response_record.v1`)
- `ReportRecord` (`fenrir.report.v1`)

## What A Run Artifact Contains

A run directory contains:

- `manifest.json`: run-level setup, model/condition identity, prompt lineage, and selected item list.
- `responses.json`: per-item outputs, errors, scoring traces, and response provenance.
- `report.json`: aggregated metrics, wrapper dependence output, condition provenance, caveats.
- `report.md`: human-readable projection of `report.json`.

## Stable Fields

Stable fields are defined by frozen schemas under `schemas/` and strict pydantic models in `fenrir/storage/models.py`.

New fields can be added only with compatible schema/version discipline.

## Safe Run Comparison Rules

Compare runs only when the following are aligned or intentionally varied:

- same `battery_id` and compatible `battery_version`
- explicit condition lineage (`condition_id`, `condition_version`, prompt hash/source)
- sampling/stopping context understood
- artifact schema versions match

Wrapper dependence should be interpreted as observed behavior shift under wrappers, not intrinsic model truth.

## What Not To Infer

Do not infer from score deltas:

- consciousness or intent,
- stable inner values,
- absolute aligned/safe/unsafe labels,
- clinical or psychiatric diagnosis.

## Migration Policy

Legacy run artifacts produced before contract freeze are non-canonical for longitudinal comparisons unless migrated to the frozen shape.

Use:

- `scripts/validate_artifacts.py --write-schemas`
- `scripts/validate_artifacts.py --runs-root <path>`

to verify contract compliance.
