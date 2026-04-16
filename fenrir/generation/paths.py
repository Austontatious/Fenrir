from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fenrir.generation.schemas import REPO_ROOT


@dataclass(frozen=True)
class SeedSurfacePaths:
    repo_root: Path
    battery_root: Path
    seed_root: Path
    generated_root: Path
    generated_raw_root: Path
    review_root: Path
    curated_root: Path
    metadata_root: Path
    schemas_root: Path


def seed_surface_paths(*, battery_id: str, repo_root: Path = REPO_ROOT) -> SeedSurfacePaths:
    battery_root = (repo_root / "batteries" / battery_id).resolve()
    seed_root = (battery_root / "seeds").resolve()
    return SeedSurfacePaths(
        repo_root=repo_root.resolve(),
        battery_root=battery_root,
        seed_root=seed_root,
        generated_root=(seed_root / "generated").resolve(),
        generated_raw_root=(seed_root / "generated" / "raw").resolve(),
        review_root=(seed_root / "review").resolve(),
        curated_root=(seed_root / "curated").resolve(),
        metadata_root=(battery_root / "metadata").resolve(),
        schemas_root=(battery_root / "schemas").resolve(),
    )


def ensure_within_repo(path: Path, *, repo_root: Path = REPO_ROOT) -> Path:
    resolved = path.resolve()
    root = repo_root.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path escapes repository root: {resolved}")
    return resolved


def ensure_within_allowed_roots(path: Path, *, allowed_roots: list[Path], label: str) -> Path:
    resolved = ensure_within_repo(path)
    allowed = [root.resolve() for root in allowed_roots]
    if not any(resolved.is_relative_to(root) for root in allowed):
        rendered = ", ".join(str(root) for root in allowed)
        raise ValueError(f"{label} path must be under one of: {rendered}. Got: {resolved}")
    return resolved
