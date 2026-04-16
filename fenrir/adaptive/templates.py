from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import yaml

from fenrir.adaptive.schemas import AdaptiveTemplateFamily


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE_ROOT = REPO_ROOT / "batteries" / "frontier_alignment_v1" / "adaptive" / "templates"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "batteries" / "frontier_alignment_v1" / "adaptive" / "schemas" / "adaptive_template.schema.json"


class AdaptiveTemplateError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AdaptiveTemplateError(f"Schema payload must be object: {path}")
    return payload


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AdaptiveTemplateError(f"Template payload must be object: {path}")
    return payload


def list_template_paths(template_root: Path = DEFAULT_TEMPLATE_ROOT) -> list[Path]:
    if not template_root.exists():
        return []
    return sorted(path for path in template_root.glob("*.yaml") if path.is_file())


def load_template_families(
    template_root: Path = DEFAULT_TEMPLATE_ROOT,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> list[AdaptiveTemplateFamily]:
    paths = list_template_paths(template_root)
    if not paths:
        raise AdaptiveTemplateError(f"No adaptive templates found under {template_root}")

    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)

    templates: list[AdaptiveTemplateFamily] = []
    for path in paths:
        payload = _load_yaml(path)
        errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
        if errors:
            message = "; ".join(
                f"{'.'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
                for err in errors
            )
            raise AdaptiveTemplateError(f"Template schema violation in {path.name}: {message}")

        templates.append(AdaptiveTemplateFamily.model_validate(payload))

    return templates
