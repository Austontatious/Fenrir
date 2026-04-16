#!/usr/bin/env python3
"""Check whether changed files stay inside an explicit allowlist scope."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fenrir.workspace.scope import classify_paths, parse_git_status_porcelain


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check changed paths against an allowlist scope")
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        help="Repo-relative file or directory allowed in this task scope. Repeat as needed.",
    )
    parser.add_argument(
        "--allow-file",
        type=Path,
        default=None,
        help="Optional newline-delimited file of repo-relative allowlist paths.",
    )
    parser.add_argument(
        "--staged-only",
        action="store_true",
        help="Only inspect staged file paths (git diff --cached --name-only).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-error informational output.",
    )
    return parser.parse_args(argv)


def _load_allow_file(path: Path | None) -> list[str]:
    if path is None:
        return []
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        lines.append(value)
    return lines


def _changed_paths(*, staged_only: bool) -> list[str]:
    if staged_only:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            check=True,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        return sorted(set(lines))

    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return parse_git_status_porcelain(proc.stdout)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    allowlist = [*args.allow, *_load_allow_file(args.allow_file)]
    if not allowlist:
        raise SystemExit("Scope check needs at least one --allow entry or --allow-file.")

    changed = _changed_paths(staged_only=args.staged_only)
    result = classify_paths(changed_paths=changed, allowlist=allowlist)

    payload = {
        "repo_root": str(REPO_ROOT),
        "allowlist": allowlist,
        "changed_paths": result.changed_paths,
        "in_scope_paths": result.in_scope_paths,
        "out_of_scope_paths": result.out_of_scope_paths,
        "ok": result.ok,
        "staged_only": args.staged_only,
    }

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif not args.quiet:
        print(f"[info] changed paths: {len(result.changed_paths)}")
        print(f"[info] in scope: {len(result.in_scope_paths)}")
        print(f"[info] out of scope: {len(result.out_of_scope_paths)}")
        if result.out_of_scope_paths:
            print("[fail] unexpected changed paths:")
            for path in result.out_of_scope_paths:
                print(f"  - {path}")
        else:
            print("[ok] all changed paths are within the declared scope")

    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
