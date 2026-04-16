# Data Model and Versioning

## Contract Freeze Scope

Fenrir freezes three run artifact contracts in this phase:

- `schemas/run_manifest.schema.json`
- `schemas/response_record.schema.json`
- `schemas/report.schema.json`

These are generated from strict pydantic models in `fenrir/storage/models.py`.

## Run Manifest (`fenrir.run_manifest.v1`)

Stable fields:

- `schema_version`
- `run_id`
- `battery_id`
- `battery_version`
- `model_target`
- `model_adapter`
- `condition_id`
- `condition_version`
- `system_prompt_hash`
- `system_prompt_source`
- `stress_profile_id`
- `sampling_config`
- `stopping_policy`
- `selected_item_ids`
- `created_at`
- `fenrir_version`

## Response Record (`fenrir.response_record.v1`)

Stable fields:

- `schema_version`
- `run_id`
- `item_id`
- `family`
- `condition_id`
- `condition_version`
- `raw_response`
- `parsed_response`
- `adapter_metadata`
- `latency_ms`
- `temperature`
- `seed`
- `error_state`
- `scoring_trace`
- `provenance`

`scoring_trace` entries preserve rubric id, triggered feature, score value, contradiction/ambiguity flags, and low-confidence marker.

`provenance` preserves battery/item/model/prompt lineage used for the response.

## Report (`fenrir.report.v1`)

Stable fields:

- `schema_version`
- `run_id`
- `summary`
- `trait_scores`
- `risk_flags`
- `stability_metrics`
- `wrapper_dependence`
- `contradictions`
- `coverage`
- `condition_provenance`
- `caveats`
- `prohibited_inferences`
- `report_version`

`wrapper_dependence` includes:

- numeric `index`
- qualitative `bucket` (`low`, `moderate`, `high`)
- explicit `explanation`
- pairwise deltas map

## Condition Lineage Semantics

- `condition_id`: logical condition identity (`raw_minimal`, `eval_control`, `production_wrapper`, `eval_control_stress`).
- `condition_version`: version of the condition definition itself.
- `system_prompt_source`: prompt file path or inline identifier.
- `system_prompt_hash`: hash of the concrete system prompt text used in run.
- `prompt_template_version`: version of prompt template contract for that condition.
- `stress_profile_id` / `stress_profile_version`: stress manipulations lineage when applicable.
- `production_wrapper_source`: source identifier for production-wrapper text/config.

## Version Discipline

Use semantic versioning across battery content and contracts.

- `patch`: typo fixes, metadata-only edits, doc clarifications, no scoring/output contract change.
- `minor`: additive backward-compatible fields/content that keep existing comparability intact.
- `major`: breaking changes to run/response/report shape, scoring semantics, or condition meaning.

Required versioned surfaces:

- battery version
- item version
- schema version
- condition version
- prompt template version
- report version

## Migration Notes

Pre-freeze artifacts created before this phase may not contain:

- `model_adapter` and prompt provenance fields in manifest,
- `run_id` / `family` / `scoring_trace` / typed provenance in response records,
- `condition_provenance` and structured wrapper dependence in report.

Treat those older artifacts as legacy and non-comparable to `*.v1` contract outputs unless migrated.

Use `scripts/validate_artifacts.py` to enforce contract compliance for new runs.
