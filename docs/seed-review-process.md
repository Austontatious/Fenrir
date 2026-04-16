# Fenrir Seed Review Process

## Claims Discipline

Fenrir seed artifacts are **draft behavioral probes**.
They are not validated clinical instruments and must not be represented as psychometrically validated scales.

## Review States and Criteria

### `draft`
Machine-generated or newly authored candidate item awaiting human review.

### `reviewed`
Minimum criteria:

- schema valid
- metadata complete
- dedupe/lint checked
- human has inspected item

### `curated`
Minimum criteria:

- options are balanced/plausible
- tradeoff is non-obvious
- diagnostic value judged adequate
- no redundant near-duplicate already curated

### `promoted`
Minimum criteria:

- item used successfully in at least one controlled run
- scoring behavior acceptable
- no major ambiguity or critical failure discovered

### `rejected`
Item is removed from active curation due to structural weakness or low diagnostic value.

### `rewrite_requested`
Item has potential but requires targeted edits before re-review.

## Allowed Transition Pattern

Primary path:

- `draft -> reviewed -> curated -> promoted`

Fallback paths:

- `draft -> rewrite_requested -> reviewed`
- `reviewed -> rewrite_requested`
- `reviewed -> rejected`
- `curated -> rewrite_requested`
- `promoted -> rewrite_requested`

## Reviewer Actions and Reason Codes

Recommended action field in review packets:

- `keep`
- `revise`
- `reject`

Standard reason codes:

- `OBVIOUS_VIRTUE_SIGNAL`
- `OPTION_ASYMMETRY`
- `REPEATED_SKELETON`
- `BLAND_NON_DIAGNOSTIC`
- `MISSING_REALISTIC_PRESSURE`
- `METADATA_DRIFT`
- `SCORING_STUB_WEAK`

## Practical Review Loop

1. Validate and lint:
   - `python3 scripts/validate_seed_bank.py --input batteries/frontier_alignment_v1/seeds/generated`
2. Export reviewer packet:
   - `python3 scripts/export_seed_review.py --input batteries/frontier_alignment_v1/seeds/generated`
3. Mark action + reason code for each item.
4. Apply edits and set `review_status` accordingly.
5. Move high-confidence items to `seeds/curated/`.
