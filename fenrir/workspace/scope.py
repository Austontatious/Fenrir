from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath


def _normalize_repo_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized.strip("/")


def parse_git_status_porcelain(porcelain: str) -> list[str]:
    paths: list[str] = []
    for raw_line in porcelain.splitlines():
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue
        if len(line) < 4:
            continue
        payload = line[3:].strip()
        if " -> " in payload:
            _, payload = payload.split(" -> ", 1)
        normalized = _normalize_repo_path(payload)
        if normalized:
            paths.append(normalized)
    return sorted(set(paths))


def _is_allowed(path: str, allowlist: list[str]) -> bool:
    candidate = PurePosixPath(_normalize_repo_path(path))
    for raw_allowed in allowlist:
        allowed = _normalize_repo_path(raw_allowed)
        if not allowed:
            continue
        allowed_path = PurePosixPath(allowed)
        if candidate == allowed_path or allowed_path in candidate.parents:
            return True
    return False


@dataclass(frozen=True)
class ScopeCheckResult:
    changed_paths: list[str]
    in_scope_paths: list[str]
    out_of_scope_paths: list[str]

    @property
    def ok(self) -> bool:
        return not self.out_of_scope_paths


def classify_paths(*, changed_paths: list[str], allowlist: list[str]) -> ScopeCheckResult:
    cleaned_allow = [_normalize_repo_path(path) for path in allowlist if _normalize_repo_path(path)]
    in_scope = [path for path in changed_paths if _is_allowed(path, cleaned_allow)]
    out_of_scope = [path for path in changed_paths if path not in in_scope]
    return ScopeCheckResult(
        changed_paths=changed_paths,
        in_scope_paths=in_scope,
        out_of_scope_paths=out_of_scope,
    )
