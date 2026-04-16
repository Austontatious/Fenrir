# Data Model and Versioning

## Versioning Rules

- Battery specs carry `schema_version` (current: `fenrir.battery.v1`).
- External response/report contracts use JSON Schema IDs.
- Breaking schema changes require version bumps and migration notes.

## Item Fields

- `item_id`
- `battery_id`
- `version`
- `family` (`trait`, `sjt`, `redteam`, `consistency_probe`, `paraphrase`)
- `target_dimensions`
- `prompt`
- `response_schema_ref`
- `scoring_refs`
- `difficulty`
- `sensitivity_tags`
- `variant_group`
- `notes`

## Run Manifest Fields

- `run_id`
- `battery_id`
- `battery_version`
- `model_target`
- `condition_id`
- `sampling_config`
- `stopping_policy`
- `selected_items`
- `created_at`

## Response Record Fields

- `item_id`
- `raw_response`
- `parsed_response`
- `adapter_metadata`
- `latency_ms`
- `condition_id`
- `temperature`
- `seed`
- `error_state`

## Report Fields

- `run_id`
- `summary`
- `trait_scores`
- `risk_flags`
- `stability_metrics`
- `wrapper_dependence`
- `contradictions`
- `coverage`
- `caveats`
- `prohibited_inferences`
