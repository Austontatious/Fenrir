# Evaluation Conditions

Fenrir compares behavior across explicit condition contexts. Every run stores condition lineage so wrapper effects are auditable.

## Condition Identity vs Prompt vs Stress vs Sampling

- **Condition identity**: logical mode (`raw_minimal`, `eval_control`, `production_wrapper`, `eval_control_stress`).
- **Prompt content**: exact system prompt text/hash used in a specific run.
- **Stress profile**: pressure manipulation profile attached to stress conditions.
- **Sampling config**: runtime decoding settings (`temperature`, `seed`, token limits); this is not part of condition identity.

## Provenance Fields Stored Per Run

- `condition_id`
- `condition_version`
- `system_prompt_source`
- `system_prompt_hash`
- `prompt_template_version`
- `inline_prompt_hash` (when condition prompt is runtime-generated)
- `stress_profile_id` / `stress_profile_version` (if used)
- `production_wrapper_source` (for wrapper file/config lineage)

## raw_minimal

Purpose: minimal orchestration for interface sanity checks.

- Version: `1.0.0`
- Prompt template: `raw_minimal.prompt.v1`
- Stress profile: none

## eval_control

Purpose: neutral measurement condition for cross-run comparability.

- Version: `1.0.0`
- Prompt template: `eval_control.prompt.v1`
- Stress profile: none

## production_wrapper

Purpose: compare production wrapper behavior against `eval_control`.

- Version: `1.0.0`
- Prompt template: `production_wrapper.prompt.v1`
- Prompt source: file placeholder or `inline:production_wrapper`
- Provenance must include `production_wrapper_source`

## eval_control_stress

Purpose: hold control framing constant while applying pressure manipulations.

- Version: `1.0.0`
- Prompt template: `eval_control_stress.prompt.v1`
- Stress profile: `default_stress_profile@1.0.0`

## Comparison Guidance

For wrapper dependence interpretation:

- Compare canonical pairs where available:
  - raw -> control
  - control -> production
  - control -> stress
- Avoid interpreting pair deltas when condition provenance differs unexpectedly (prompt hash mismatch, unknown wrapper source, or mixed stress profile versions).
