from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from fenrir.batteries.schemas import BatteryItem, BatterySpec, LoadedBattery


class BatteryLoadError(ValueError):
    pass


def load_battery(battery_root: Path) -> LoadedBattery:
    battery_path = battery_root / "battery.yaml"
    if not battery_path.exists():
        raise BatteryLoadError(f"battery.yaml not found under {battery_root}")

    payload = _load_yaml_object(battery_path)
    spec = BatterySpec.model_validate(payload)

    items: list[BatteryItem] = []
    for item_ref in spec.item_files:
        item_path = battery_root / item_ref
        item_payload = _load_yaml_object(item_path)
        for entry in _normalize_item_payload(item_payload):
            merged = {
                "battery_id": spec.metadata.id,
                "version": spec.metadata.version,
                **entry,
            }
            items.append(BatteryItem.model_validate(merged))

    if not items:
        raise BatteryLoadError(f"battery {spec.metadata.id} has no items")

    return LoadedBattery(spec=spec, items=items)


def _load_yaml_object(path: Path) -> dict[str, Any]:
    decoded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict):
        raise BatteryLoadError(f"expected object payload in {path}")
    return decoded


def _normalize_item_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if "items" in payload:
        items = payload["items"]
        if not isinstance(items, list):
            raise BatteryLoadError("items key must contain a list")
        normalized: list[dict[str, Any]] = []
        for entry in items:
            if not isinstance(entry, dict):
                raise BatteryLoadError("every item entry must be an object")
            normalized.append(entry)
        return normalized
    return [payload]
