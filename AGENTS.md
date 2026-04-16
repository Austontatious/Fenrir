# AGENTS.md

This repo follows:
- `/home/unix/codex-standards/BASELINE.md`
Repo-specific overrides and invariants below.

## Muninn Memory Integration (Required)
Use Muninn as durable memory for decisions, constraints, runbooks, interfaces, and validated lessons.

On task start (before substantial edits):
- Call `muninn.spaces.resolve` with current absolute `cwd`.
- Use the returned `space.key` as `<resolved-space-key>` for retrieval calls.
- Preferred: call `muninn.rehydrate.bundle` with:
  - `lens`: `{space_key:"<resolved-space-key>", scope:"soft", kinds:["decision","constraint","runbook","interface"], limit:12}`
  - `query`: short task summary.
- Compatibility sequence (when bundle is unavailable):
  - `muninn.cards.recent` with `lens`: `{space_key:"<resolved-space-key>", scope:"strict", kinds:["decision","constraint","runbook","interface"], limit:12}`
  - `muninn.cards.search` with `lens`: `{space_key:"<resolved-space-key>", scope:"soft", kinds:["decision","constraint","runbook","interface"], limit:12}` and short task query.
- If `space_key` is unavailable, pass a full lens with `space:"auto"` and absolute `cwd`.
- Use retrieved memory to inform plan and edits before implementing.

On meaningful completion:
- Write durable outcomes via `muninn.cards.upsert` (target `1-3` cards per task).
- Send object-shaped upsert arguments only (never prose strings for `card`).
- For `decision`, `constraint`, `interface`, and `runbook`, include at least one evidence ref whenever applicable.
- If evidence is unavailable, do not fabricate it.

## Mission
Fenrir provides an MCP-native behavioral evaluation harness for frontier LLMs.

The platform measures observed tendencies under explicit conditions and compares wrapper effects without asserting unobservable internals.

## Repo-Specific Invariants
- Keep batteries as data (`battery.yaml` + item/rubric/schema files), not hardcoded logic.
- Keep adapter transport concerns separate from battery orchestration and scoring.
- Keep scoring interpretable and rubric-oriented before introducing learned scorers.
- Do not claim diagnosis, alignment proof, or model-internal intent from Fenrir outputs.
- Preserve condition comparability: same items, explicit condition id, explicit sampling/stopping config.

## Definition of Done
- Battery load and run path works end-to-end for at least one battery.
- JSON and markdown report artifacts are emitted.
- MCP tool skeleton exposes list/describe/run/compare/report tool surfaces.
- `pytest -q` passes.
- Standards checks pass (`python3 evals/runner.py --check`).

## Architecture and Operations Source of Truth
- Architecture truth: `docs/architecture.md`
- Operational procedures: `RUNBOOK.md` (if present)

## Overrides
- `GIT_POLICY: conservative`
- rationale: default non-destructive posture.
