# Fenrir Workspace Safety

This workflow exists to prevent unrelated file drift during Fenrir tasks.

## Scope-First Rule

Before edits, define the intended write scope as repo-relative paths.

Example scope for seed-generation tasks:

- `fenrir/generation`
- `fenrir/workspace`
- `scripts`
- `docs`
- `tests`
- `batteries/frontier_alignment_v1/seeds`
- `batteries/frontier_alignment_v1/metadata`
- `batteries/frontier_alignment_v1/schemas`

## Allowlist Staging Workflow

1. Define scope paths.
2. Run `git status --short` and confirm changed files.
3. Run scope check:
   - `python3 scripts/check_workspace_scope.py --allow <path> --allow <path> ...`
4. Stage only explicit allowlist paths:
   - `git add <file-or-dir> ...`
5. Re-run staged scope check:
   - `python3 scripts/check_workspace_scope.py --staged-only --allow <path> ...`
6. Commit only after out-of-scope paths are zero.

Make shortcuts:

- `make workspace-scope ALLOW='docs scripts tests'`
- `make seed-workspace-scope`

## Output Boundaries

Use these output classes consistently:

- Draft seed generation: `batteries/frontier_alignment_v1/seeds/generated/`
- Raw generation request/response artifacts: `batteries/frontier_alignment_v1/seeds/generated/raw/`
- Review packets/exports: `batteries/frontier_alignment_v1/seeds/review/`
- Curated assets: `batteries/frontier_alignment_v1/seeds/curated/`
- Runtime execution artifacts: `artifacts/runs/` and `artifacts/comparisons/`

Avoid default writes to tracked docs or unrelated directories from automation scripts.

## Script Safety Expectations

- Prefer `--dry-run` before write-heavy runs.
- Prefer explicit `--output` / `--artifact-dir` when deviating from defaults.
- Do not overwrite existing files without explicit `--overwrite`.
- Keep normal test runs side-effect free (temp dirs for generated test artifacts).
