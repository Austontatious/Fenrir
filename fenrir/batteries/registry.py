from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fenrir.batteries.loader import load_battery
from fenrir.batteries.schemas import LoadedBattery


@dataclass(frozen=True)
class BatteryDescriptor:
    id: str
    version: str
    path: Path
    description: str


def list_batteries(battery_root: Path) -> list[BatteryDescriptor]:
    descriptors: list[BatteryDescriptor] = []
    for candidate in sorted(battery_root.iterdir() if battery_root.exists() else []):
        battery_file = candidate / "battery.yaml"
        if not candidate.is_dir() or not battery_file.exists():
            continue
        loaded = load_battery(candidate)
        descriptors.append(
            BatteryDescriptor(
                id=loaded.spec.metadata.id,
                version=loaded.spec.metadata.version,
                path=candidate,
                description=loaded.spec.metadata.description,
            )
        )
    return descriptors


def get_battery(battery_root: Path, battery_id: str) -> LoadedBattery:
    for descriptor in list_batteries(battery_root):
        if descriptor.id == battery_id:
            return load_battery(descriptor.path)
    raise KeyError(f"unknown battery_id: {battery_id}")
