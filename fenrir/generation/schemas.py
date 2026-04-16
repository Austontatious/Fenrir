from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BATTERY_ID = "frontier_alignment_v1"
DEFAULT_SCHEMA_DIR = REPO_ROOT / "batteries" / DEFAULT_BATTERY_ID / "schemas"
DEFAULT_METADATA_DIR = REPO_ROOT / "batteries" / DEFAULT_BATTERY_ID / "metadata"

SUPPORTED_FAMILIES = {
    "trait_forced_choice",
    "sjt_seed",
    "redteam_behavioral_probe",
    "consistency_variant",
}


class SchemaValidationError(ValueError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Schema at {path} must decode to a JSON object")
    return payload


def load_seed_item_schema(schema_dir: Path = DEFAULT_SCHEMA_DIR) -> dict[str, Any]:
    return _read_json(schema_dir / "seed_item.schema.json")


def load_seed_batch_schema(schema_dir: Path = DEFAULT_SCHEMA_DIR) -> dict[str, Any]:
    return _read_json(schema_dir / "seed_batch.schema.json")


def _sorted_errors(validator: Draft202012Validator, instance: Mapping[str, Any]) -> list[str]:
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    messages: list[str] = []
    for err in errors:
        path = ".".join(str(part) for part in err.path)
        label = path or "<root>"
        messages.append(f"{label}: {err.message}")
    return messages


def validate_item(item: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    return _sorted_errors(validator, item)


def validate_batch(batch: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    return _sorted_errors(validator, batch)


def require_valid_item(item: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    issues = validate_item(item, schema)
    if issues:
        raise SchemaValidationError("; ".join(issues))


def require_valid_batch(batch: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    issues = validate_batch(batch, schema)
    if issues:
        raise SchemaValidationError("; ".join(issues))


def sanitize_schema_for_responses(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce canonical schema to the strict subset accepted by Responses API."""

    allowed_keys = {
        "type",
        "properties",
        "required",
        "items",
        "additionalProperties",
        "enum",
        "const",
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
    }

    def _clean(value: Any, *, in_properties: bool = False) -> Any:
        if isinstance(value, dict):
            if in_properties:
                return {key: _clean(val) for key, val in value.items()}
            dropped = {"$schema", "$id", "title", "description", "examples", "default"}
            cleaned: dict[str, Any] = {}
            for key, val in value.items():
                if key in dropped:
                    continue
                if key not in allowed_keys:
                    continue
                cleaned[key] = _clean(val, in_properties=(key == "properties"))
            return cleaned
        if isinstance(value, list):
            return [_clean(item) for item in value]
        return value

    cleaned = _clean(deepcopy(dict(schema)))
    if not isinstance(cleaned, dict):
        raise ValueError("sanitized schema must stay object-shaped")
    return cleaned


def _enforce_required_properties(schema: dict[str, Any]) -> dict[str, Any]:
    def _walk(node: Any) -> Any:
        if isinstance(node, dict):
            node_type = node.get("type")
            properties = node.get("properties")
            if node_type == "object" and isinstance(properties, dict):
                property_keys = list(properties.keys())
                node["required"] = property_keys
                node.setdefault("additionalProperties", False)
                for key, value in properties.items():
                    properties[key] = _walk(value)
            items = node.get("items")
            if isinstance(items, dict):
                node["items"] = _walk(items)
            elif isinstance(items, list):
                node["items"] = [_walk(entry) for entry in items]
            return node
        if isinstance(node, list):
            return [_walk(item) for item in node]
        return node

    return _walk(deepcopy(schema))


def _restrict_items_schema(
    batch_schema: dict[str, Any],
    *,
    family: str,
    count: int,
    battery_id: str,
    version: str,
    generation_prompt_version: str,
    generator_model: str,
) -> dict[str, Any]:
    constrained = deepcopy(batch_schema)
    props = constrained.setdefault("properties", {})
    props["battery_id"] = {"type": "string", "const": battery_id}
    props["version"] = {"type": "string", "const": version}
    props["generation_prompt_version"] = {"type": "string", "const": generation_prompt_version}
    props["generator_model"] = {"type": "string", "const": generator_model}

    items_block = props.get("items")
    if not isinstance(items_block, dict):
        raise ValueError("seed batch schema missing properties.items")
    items_block["minItems"] = count
    items_block["maxItems"] = count

    item_schema = items_block.get("items")
    if not isinstance(item_schema, dict):
        raise ValueError("seed batch schema missing properties.items.items")
    item_props = item_schema.setdefault("properties", {})
    item_props["family"] = {"type": "string", "const": family}
    item_props["battery_id"] = {"type": "string", "const": battery_id}
    item_props["version"] = {"type": "string", "const": version}
    item_props["generation_prompt_version"] = {
        "type": "string",
        "const": generation_prompt_version,
    }
    item_props["generator_model"] = {"type": "string", "const": generator_model}
    item_props["review_status"] = {"type": "string", "const": "draft"}
    return constrained


def build_generation_schema(
    *,
    seed_batch_schema: Mapping[str, Any],
    family: str,
    count: int,
    battery_id: str,
    version: str,
    generation_prompt_version: str,
    generator_model: str,
) -> dict[str, Any]:
    if family not in SUPPORTED_FAMILIES:
        raise ValueError(f"Unsupported family: {family}")
    if count <= 0:
        raise ValueError("count must be positive")

    constrained = _restrict_items_schema(
        deepcopy(dict(seed_batch_schema)),
        family=family,
        count=count,
        battery_id=battery_id,
        version=version,
        generation_prompt_version=generation_prompt_version,
        generator_model=generator_model,
    )
    sanitized = sanitize_schema_for_responses(constrained)
    return _enforce_required_properties(sanitized)


def _extract_ids(items: Iterable[Any], *, field_name: str = "id") -> list[str]:
    values: list[str] = []
    for item in items:
        if isinstance(item, dict):
            value = item.get(field_name)
            if isinstance(value, str) and value.strip():
                values.append(value.strip())
    return values


def load_dimension_ids(metadata_dir: Path = DEFAULT_METADATA_DIR) -> list[str]:
    path = metadata_dir / "dimension_taxonomy.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _extract_ids(payload.get("dimensions") or [])


def load_coverage_ids(metadata_dir: Path = DEFAULT_METADATA_DIR) -> list[str]:
    path = metadata_dir / "coverage_taxonomy.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _extract_ids(payload.get("coverage_tags") or [])


def load_pressure_ids(metadata_dir: Path = DEFAULT_METADATA_DIR) -> list[str]:
    path = metadata_dir / "coverage_taxonomy.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    tags = payload.get("pressure_tags") or []
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()]
    return []


def load_sensitivity_ids(metadata_dir: Path = DEFAULT_METADATA_DIR) -> list[str]:
    path = metadata_dir / "sensitivity_tags.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _extract_ids(payload.get("sensitivity_tags") or [])
