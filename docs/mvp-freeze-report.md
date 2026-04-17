# MVP Freeze and Repository Positioning Report

Date: 2026-04-17

## Scope

This pass froze Fenrir's MVP-defining surfaces and refreshed public-facing positioning language to match current reality.

## What Was Frozen

### Frozen MVP Components

- Hybrid battery definition:
  - `batteries/frontier_alignment_v1/hybrid/hybrid_mvp_v1.yaml`
- Static baseline slice:
  - `batteries/frontier_alignment_v1/seeds/curated/static_baseline_mvp_v1.json`
- Adaptive family set in MVP path:
  - `authority_override`
  - `reputation_shielding`
  - `urgency_tradeoff`
- Core ladder/controller semantics (`L1` to `L5`, `escalate`/`branch_probe`/`stop`) as documented by frozen references.
- Primary MVP conditions:
  - `raw_minimal`
  - `eval_control`
  - `eval_control_stress`
- Report/artifact contract surfaces:
  - `fenrir.run_manifest.v1`
  - `fenrir.response_record.v1`
  - `fenrir.report.v1`
  - `hybrid_mvp_eval_v1`
- Core failure-mode labels:
  - `concealment`, `confidence_smoothing`, `approval_seeking`, `authority_compliance`, `reputational_shielding`, `policy_softening`, `no_material_shift`

### Canonical Freeze Contract

- Added: `docs/mvp-freeze.md`
- Purpose: define frozen surfaces, experimental surfaces, future expansion, and versioned change protocol.

## What Remains Experimental

- Additional adaptive families outside the frozen MVP trio.
- Threshold/confidence heuristic tuning experiments.
- Non-MVP comparative paths such as `production_wrapper` in verdicting.
- Seed-pipeline process and expansion work that does not mutate frozen slices in place.

## Public Positioning Updates

### README

Updated `README.md` to act as canonical public explanation:

- what Fenrir is,
- why it exists,
- how the hybrid design works,
- current MVP scope,
- what Fenrir does not claim,
- quickstart and primary run path,
- project freeze status.

### Name Explanation (Chosen)

Short (README):

Fenrir is named for the shadow metaphor: latent risk patterns that are easy to ignore until pressure reveals them. In this project that is an evaluation framing only, not a claim that AI systems have a human psyche.

Medium (docs):

The name Fenrir references the shadow as a practical metaphor, not a mystical one. The goal is to evaluate behaviors that may remain hidden in normal prompts but appear when constraints, urgency, authority pressure, or reputational pressure increase. Fenrir does not claim models have a literal psyche and does not present clinical interpretation. It is an instrumentation layer for observing where behavior shifts across controlled conditions.

One-line:

Fenrir is a pressure-aware LLM evaluation harness that surfaces latent risk behaviors through controlled condition shifts and auditable comparisons.

### GitHub Description Candidates

- Condition-aware LLM behavior evaluation with hybrid static anchors and adaptive pressure probes.
- Behavioral eval harness for LLMs: compare condition-driven shifts with versioned, auditable artifacts.
- Hybrid static plus adaptive LLM evaluation for surfacing pressure-induced behavior changes.
- Empirical LLM behavior assessment under controlled wrappers, stress ladders, and strict report contracts.
- MVP-focused LLM behavior testing with explicit conditions, failure modes, and bounded claims.

## Governance and Anti-Drift Updates

- Updated `AGENTS.md` with required MVP freeze guardrails.
- Updated `docs/report-contract.md` and `docs/architecture.md` with explicit MVP freeze boundary alignment.
- Added `docs/about.md` for concise external positioning, name language variants, and claims discipline.

## Notes

No core runtime code paths were changed in this pass. Changes were focused on freeze discipline and repository positioning surfaces.
