# Repository Cleanup Report - 2026-05-28

> Status: GENERATED REPORT. This file records the conservative cleanup pass performed on 2026-05-28. Do not treat it as architecture authority; confirm current behavior against the canonical docs, code, batteries, artifacts, and tests.

## Scope

- Repository: `/mnt/data/Fenrir`
- Cleanup mode: two-pass conservative cleanup.
- Policy: preserve evidence and history; no meaningful files deleted; do not casually mutate frozen MVP surfaces.

## Pass 1 Inventory

Current canonical docs:

- `README.md` - product shape, MVP scope, setup, readout contract, non-claims, and documentation map.
- `AGENTS.md` - repo invariants, MVP freeze guardrails, workspace safety, and validation gates.
- `docs/mvp-freeze.md` - canonical MVP-surface contract.
- `docs/readout-contract.md` and `docs/report-contract.md` - readout/report contracts.
- `docs/architecture.md` - architecture source of truth.
- `docs/CODEX_STANDARDS.md` - repo-local standards contract.

Preexisting drift observed before cleanup:

- Worktree was clean before cleanup.
- Several report-named docs were present. Some are still referenced by scripts or MVP-freeze docs.

## Classification

- `CURRENT_CANONICAL`: `README.md`, `AGENTS.md`, `docs/mvp-freeze.md`, `docs/readout-contract.md`, `docs/report-contract.md`, `docs/architecture.md`, `docs/CODEX_STANDARDS.md`.
- `HISTORICAL_EVIDENCE`: `docs/archive/reports/`, old report docs, and artifact reports.
- `GENERATED_ARTIFACT`: `artifacts/runs`, `artifacts/comparisons`, and hybrid artifact outputs.
- `REVIEW_NEEDED`: none identified.

## Pass 2 Cleanup

- Added `docs/README.md` as the documentation index.
- Moved standalone historical reports to `docs/archive/reports/`.
- Added `docs/archive/reports/README.md` with historical status.
- Added this cleanup report under `reports/`.
- Updated `README.md` documentation map.
- Left `docs/adaptive-probe-v0-report.md`, `docs/hybrid-mvp-report.md`, and `docs/mvp-freeze-report.md` in place because they are referenced by scripts or MVP-freeze guidance.

## Files Moved

- `docs/gold-slice-eval-report.md` -> `docs/archive/reports/gold-slice-eval-report.md`
- `docs/seed-generation-cleanup-report.md` -> `docs/archive/reports/seed-generation-cleanup-report.md`

## Deletion Candidates Requiring Approval

- None proposed.

## Validation

Validation recorded after edits:

- `git diff --check` - passed.
- `python3 -m pytest -q tests/test_codex_standards.py --noconftest` - passed, 9 tests.
- `python3 evals/runner.py --check` - passed, 2 case files.
- `make lint` - passed.
- `bash /mnt/data/.codex_ssot/v1/tools/agents_lint.sh` - exited 0, `FAIL=0`; reported preexisting WARNs for this repo's `AGENTS.md` governance sections.

## Remaining Risk

- Future cleanup should review whether script default report paths should move to `reports/` under an explicit compatibility change. This cleanup did not change those paths.
