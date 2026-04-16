from __future__ import annotations

from pathlib import Path

from fenrir.batteries.registry import get_battery, list_batteries


def test_battery_registry_lists_seed_battery() -> None:
    root = Path(__file__).resolve().parents[1] / "batteries"
    listed = list_batteries(root)
    ids = {item.id for item in listed}
    assert "frontier_alignment_v1" in ids


def test_get_battery_loads_items() -> None:
    root = Path(__file__).resolve().parents[1] / "batteries"
    battery = get_battery(root, "frontier_alignment_v1")
    assert battery.spec.metadata.version == "0.1.0"
    assert len(battery.items) >= 4
