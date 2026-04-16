# Fenrir Seed Review Process

## Claims Discipline

Fenrir seed artifacts are **draft behavioral probes**.
They are not validated clinical instruments and should not be represented as psychometrically validated scales.

## Lifecycle

1. `draft`: machine-generated; unreviewed.
2. `reviewed`: human-reviewed and edited as needed.
3. `curated`: accepted into curated seed inventory.
4. `promoted`: selected for downstream testing batteries.
5. `rejected` or `rewrite_required`: removed or routed back to generation.

## Reviewer Goals

Reviewers should optimize for behavioral discriminability, not surface moral signaling.

Accept items that:

- encode realistic tradeoffs
- avoid obvious good/bad answer cues
- align with target dimensions and tags
- have plausible options and coherent scoring stubs

Reject or rewrite items that:

- are repetitive or near-duplicate
- moralize explicitly (easy virtue-signaling)
- have unbalanced options
- lack clear pressure context
- contain weak or mismatched metadata

## Handling Paraphrase/Consistency Groups

- `variant_group` links semantically related items.
- A group should include one conceptual probe and one or more paraphrase variants.
- If one variant is rejected for leakage or imbalance, review sibling variants for correlated flaws.
- Keep accepted variants behaviorally equivalent while varying wording and framing.

## Recommended Review Loop

1. Run validation and lint:
   - `python3 scripts/validate_seed_bank.py --input batteries/frontier_alignment_v1/seeds/generated`
2. Export review packet:
   - `python3 scripts/export_seed_review.py --input batteries/frontier_alignment_v1/seeds/generated`
3. Annotate each item with action (`accept`, `edit`, `reject`, `rewrite`).
4. Move accepted items to `seeds/curated/` with updated `review_status` and notes.
5. Regenerate gaps (dimensions/tags/families) as needed.

## Promotion Readiness (Future)

Promotion into scored batteries should happen only after:

- stability checks across paraphrase variants
- preliminary reliability and bias checks
- policy and safety review for adversarial probes
- explicit documentation of limits and intended use
