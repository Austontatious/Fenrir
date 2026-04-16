from __future__ import annotations

from fenrir.workspace.scope import classify_paths, parse_git_status_porcelain


def test_parse_git_status_porcelain_handles_mod_and_untracked() -> None:
    payload = " M scripts/generate_seed_bank.py\n?? docs/workspace-safety.md\n"
    paths = parse_git_status_porcelain(payload)
    assert paths == ["docs/workspace-safety.md", "scripts/generate_seed_bank.py"]


def test_parse_git_status_porcelain_handles_rename_arrow() -> None:
    payload = "R  docs/old.md -> docs/new.md\n"
    paths = parse_git_status_porcelain(payload)
    assert paths == ["docs/new.md"]


def test_classify_paths_reports_out_of_scope() -> None:
    result = classify_paths(
        changed_paths=[
            "scripts/generate_seed_bank.py",
            "docs/item-bank-generation.md",
            "fenrir/orchestrator/runner.py",
        ],
        allowlist=["scripts", "docs"],
    )
    assert result.ok is False
    assert result.out_of_scope_paths == ["fenrir/orchestrator/runner.py"]
