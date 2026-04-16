# Fenrir Question Bank Curation

## Why Generated Seeds Are Not Canon

Model-generated seeds are draft probes, not ground truth. They are useful for coverage bootstrapping,
but they contain recurring failure modes (obvious virtue cues, weak symmetry, repeated skeletons,
and metadata drift) that require disciplined human curation.

## Gold Slice Role

`gold_slice_v1` is a hand-reviewed anchor set used for:

- sanity checks of scoring and reporting behavior
- regression comparisons when generation prompts/lint rules change
- calibration of reviewer expectations for balanced, diagnostic items

Gold slice status is `curated`, not psychometrically validated.

## Promotion and Rejection Workflow

States:

- `draft`
- `reviewed`
- `curated`
- `promoted`
- `rejected`
- `rewrite_requested`

Typical transitions:

- `draft -> reviewed -> curated -> promoted`
- `draft -> rewrite_requested -> reviewed`
- `reviewed -> rejected`
- `curated -> rewrite_requested`

Promotion criteria:

- `draft -> reviewed`: schema valid, metadata complete, lint checked, human inspected
- `reviewed -> curated`: balanced options, non-obvious tradeoff, adequate diagnostic value, non-redundant in curated pool
- `curated -> promoted`: used in at least one controlled run, scoring behavior acceptable, no major ambiguity discovered

## Common Failure Modes

- obvious virtue signaling (one option transparently "good AI")
- weak option symmetry (one option implausible in real operations)
- repeated skeletons across stems/options
- bland non-diagnostic prompts with low pressure realism
- overconcentrated dimension/tag mappings
- scoring stubs that moralize or restate the preferred option

## Curation Loop

1. Validate seeds with lint heuristics.
2. Export review packet.
3. Annotate each item (`keep` / `revise` / `reject`) with reason codes.
4. Apply revisions and update review status.
5. Promote only after controlled-run evidence.

## Workspace Discipline

During curation passes, keep edits scoped to:

- `batteries/frontier_alignment_v1/seeds/`
- targeted docs/tests/scripts that support the same curation change

Before commit, run scoped checks from `docs/workspace-safety.md` to prevent unrelated drift from execution artifacts or parallel tasks.
