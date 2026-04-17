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

## MVP Freeze Guardrails (Required)
- Treat `docs/mvp-freeze.md` as the canonical MVP-surface contract.
- Do not casually mutate frozen MVP artifacts in place.
- Any behavioral change to a frozen MVP surface requires:
  - a new explicit versioned artifact path,
  - a rationale note and compatibility impact summary,
  - updated references in docs/scripts as needed.
- Experimental work must live beside MVP paths, not silently inside them.
- Public docs must keep explicit non-claims language (no diagnosis/alignment-proof/intent claims).

## Workspace Safety (Required)
- Declare intended write scope before edits and keep the scope repo-local.
- Stage with explicit allowlist paths only (`git add <paths>`), never blanket staging.
- Run `python3 scripts/check_workspace_scope.py --staged-only --allow <path> ...` before commit.
- Report excluded out-of-scope changes in task summaries.
- Keep artifact classes separated:
  - seed drafts/review/curation under `batteries/frontier_alignment_v1/seeds/`
  - execution artifacts under `artifacts/runs` and `artifacts/comparisons`
  - do not default automation writes into unrelated tracked docs/paths

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
