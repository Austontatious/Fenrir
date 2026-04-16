from __future__ import annotations

from pathlib import Path

import pytest

from fenrir.generation.paths import ensure_within_allowed_roots, seed_surface_paths


def test_seed_surface_paths_resolve_under_repo() -> None:
    surface = seed_surface_paths(battery_id="frontier_alignment_v1")
    assert surface.seed_root.name == "seeds"
    assert surface.generated_root.is_relative_to(surface.seed_root)
    assert surface.review_root.is_relative_to(surface.seed_root)


def test_ensure_within_allowed_roots_rejects_escape(tmp_path: Path) -> None:
    outsider = tmp_path / "external" / "x.json"
    outsider.parent.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError):
        ensure_within_allowed_roots(
            outsider,
            allowed_roots=[Path("/mnt/data/Fenrir/batteries/frontier_alignment_v1/seeds/generated")],
            label="output",
        )
