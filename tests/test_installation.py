from __future__ import annotations

import json
from pathlib import Path
import socket

from fenrir.config import FenrirConfig
from fenrir.local_runtime import (
    LOCAL_STATE_SCHEMA_VERSION,
    LocalServiceState,
    default_local_state,
    load_local_state,
    load_local_state_result,
    resolve_service_port,
    save_local_state,
)
import fenrir.server as fenrir_server
import fenrir.local_runtime as local_runtime
import scripts.check_fenrir_env as check_fenrir_env
import scripts.install_fenrir as install_fenrir
import scripts.start_fenrir as start_fenrir


def test_resolve_service_port_scans_when_requested_port_is_taken() -> None:
    host = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        occupied = int(sock.getsockname()[1])
        resolved = resolve_service_port(host, occupied, scan_limit=8)
    assert resolved != occupied


def test_local_state_roundtrip(tmp_path: Path) -> None:
    cfg = FenrirConfig.from_env()
    state = default_local_state(cfg)
    state.service_port = 9876
    state.endpoint.api_key = "test_secret_key"
    path = tmp_path / "local_config.json"

    save_local_state(path, state)
    loaded = load_local_state(path, defaults=LocalServiceState(service_host="127.0.0.1", service_port=8765))

    assert loaded.service_port == 9876
    assert loaded.endpoint.api_key == "test_secret_key"
    assert loaded.endpoint.to_public_dict()["has_api_key"] is True


def test_load_current_version_config(tmp_path: Path) -> None:
    cfg = FenrirConfig.from_env()
    defaults = default_local_state(cfg)
    state = default_local_state(cfg)
    state.endpoint.model = "custom-model-v1"
    path = tmp_path / "local_config.json"
    save_local_state(path, state)

    result = load_local_state_result(path, defaults=defaults)
    assert result.source_version == LOCAL_STATE_SCHEMA_VERSION
    assert result.migrated is False
    assert result.repaired is False
    assert result.should_persist is False
    assert result.state.endpoint.model == "custom-model-v1"


def test_migrate_older_version_config(tmp_path: Path) -> None:
    cfg = FenrirConfig.from_env()
    defaults = default_local_state(cfg)
    path = tmp_path / "local_config.json"
    legacy_payload = {
        "service": {"host": "127.0.0.1", "port": 9800},
        "mcp": {"enabled": True, "host": "127.0.0.1", "port": 9900},
        "battery_id": "frontier_alignment_v1",
        "conditions": ["eval_control"],
        "endpoint": {
            "provider": "openai_compatible",
            "base_url": "https://example.invalid/v1",
            "api_key": "sk-legacy",
            "model": "legacy-model",
            "timeout_seconds": 55.0,
        },
    }
    path.write_text(json.dumps(legacy_payload), encoding="utf-8")

    result = load_local_state_result(path, defaults=defaults)
    assert result.source_version is None
    assert result.migrated is True
    assert result.repaired is False
    assert result.should_persist is True
    assert result.state.endpoint.model == "legacy-model"
    assert any("Migrated legacy local state" in message for message in result.messages)


def test_missing_version_field_migrates_legacy_shape(tmp_path: Path) -> None:
    cfg = FenrirConfig.from_env()
    defaults = default_local_state(cfg)
    path = tmp_path / "local_config.json"
    path.write_text(
        json.dumps(
            {
                "service": {"host": "127.0.0.1", "port": 9055},
                "endpoint": {"model": "missing-version-model"},
            }
        ),
        encoding="utf-8",
    )
    result = load_local_state_result(path, defaults=defaults)
    assert result.migrated is True
    assert result.should_persist is True
    assert result.state.service_port == 9055
    assert result.state.endpoint.model == "missing-version-model"


def test_malformed_config_gracefully_repairs(tmp_path: Path) -> None:
    cfg = FenrirConfig.from_env()
    defaults = default_local_state(cfg)
    path = tmp_path / "local_config.json"
    path.write_text("{not-valid-json", encoding="utf-8")

    result = load_local_state_result(path, defaults=defaults)
    assert result.repaired is True
    assert result.should_persist is True
    assert result.state.endpoint.model == defaults.endpoint.model
    assert any("invalid JSON" in message for message in result.messages)


def test_save_local_state_atomic_success(tmp_path: Path) -> None:
    cfg = FenrirConfig.from_env()
    state = default_local_state(cfg)
    state.endpoint.model = "atomic-model"
    path = tmp_path / "local_config.json"

    save_local_state(path, state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == LOCAL_STATE_SCHEMA_VERSION
    assert payload["endpoint"]["model"] == "atomic-model"


def test_save_local_state_atomic_failure_preserves_existing(tmp_path: Path, monkeypatch) -> None:
    cfg = FenrirConfig.from_env()
    path = tmp_path / "local_config.json"
    original = default_local_state(cfg)
    original.endpoint.model = "before-failure"
    save_local_state(path, original)
    before = path.read_text(encoding="utf-8")

    def _raise_replace(*_args, **_kwargs):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(local_runtime.os, "replace", _raise_replace)
    mutated = default_local_state(cfg)
    mutated.endpoint.model = "after-failure"

    try:
        save_local_state(path, mutated)
        assert False, "save_local_state should fail when os.replace fails"
    except RuntimeError as exc:
        assert "Failed to write local state atomically" in str(exc)

    assert path.read_text(encoding="utf-8") == before


def test_repeated_atomic_writes_stable(tmp_path: Path) -> None:
    cfg = FenrirConfig.from_env()
    path = tmp_path / "local_config.json"
    state = default_local_state(cfg)

    for idx in range(3):
        state.endpoint.model = f"stable-model-{idx}"
        save_local_state(path, state)
        loaded = load_local_state(path, defaults=default_local_state(cfg))
        assert loaded.endpoint.model == f"stable-model-{idx}"


def test_install_persist_state_preserves_existing_by_default(tmp_path: Path) -> None:
    cfg = FenrirConfig.from_env()
    path = tmp_path / "local_config.json"
    existing = default_local_state(cfg)
    existing.endpoint.model = "custom-model"
    existing.endpoint.api_key = "sk-custom"
    existing.conditions = ["eval_control"]
    save_local_state(path, existing)

    install_fenrir._persist_state(
        cfg,
        host="127.0.0.1",
        port=9010,
        overwrite_state=False,
        state_path=path,
    )
    loaded = load_local_state(path, defaults=default_local_state(cfg))
    assert loaded.service_port == 9010
    assert loaded.endpoint.model == "custom-model"
    assert loaded.endpoint.api_key == "sk-custom"
    assert loaded.conditions == ["eval_control"]


def test_install_persist_state_can_explicitly_overwrite(tmp_path: Path) -> None:
    cfg = FenrirConfig.from_env()
    path = tmp_path / "local_config.json"
    existing = default_local_state(cfg)
    existing.endpoint.model = "custom-model"
    existing.endpoint.api_key = "sk-custom"
    save_local_state(path, existing)

    install_fenrir._persist_state(
        cfg,
        host="127.0.0.1",
        port=9011,
        overwrite_state=True,
        state_path=path,
    )
    loaded = load_local_state(path, defaults=default_local_state(cfg))
    assert loaded.service_port == 9011
    assert loaded.endpoint.model == cfg.openai_model
    assert loaded.endpoint.api_key == cfg.openai_api_key


def test_start_script_handles_port_resolution_failure(monkeypatch, capsys) -> None:
    def _raise(*_args, **_kwargs):
        raise RuntimeError("port scan failed")

    monkeypatch.setattr(start_fenrir, "resolve_service_port", _raise)
    rc = start_fenrir.main(["--host", "127.0.0.1", "--port", "8765"])
    output = capsys.readouterr().out

    assert rc == 2
    assert "error" in output
    assert "choose another --port" in output


def test_install_script_handles_port_resolution_failure(monkeypatch, capsys) -> None:
    def _raise(*_args, **_kwargs):
        raise RuntimeError("port scan failed")

    monkeypatch.setattr(install_fenrir, "_ensure_env_file", lambda: Path(".env"))
    monkeypatch.setattr(install_fenrir, "resolve_service_port", _raise)
    rc = install_fenrir.main(["--skip-install", "--host", "127.0.0.1", "--port", "8765"])
    output = capsys.readouterr().out

    assert rc == 2
    assert "error" in output
    assert "choose another --port" in output


def test_server_local_service_handles_port_resolution_failure(monkeypatch, capsys) -> None:
    cfg = FenrirConfig.from_env()

    def _raise(*_args, **_kwargs):
        raise RuntimeError("port scan failed")

    monkeypatch.setattr(fenrir_server, "resolve_service_port", _raise)
    rc = fenrir_server._run_local_service(
        config=cfg,
        host="127.0.0.1",
        port=8765,
        strict_port=False,
        scan_limit=10,
    )
    output = capsys.readouterr().out

    assert rc == 2
    assert "error" in output


def test_check_env_treats_fallback_port_as_runnable(monkeypatch) -> None:
    monkeypatch.setattr(check_fenrir_env.sys, "version_info", (3, 11, 0))
    monkeypatch.setattr(check_fenrir_env, "_check_imports", lambda: (True, []))
    monkeypatch.setattr(check_fenrir_env, "is_port_open", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(check_fenrir_env, "resolve_service_port", lambda *_args, **_kwargs: 9999)
    rc = check_fenrir_env.main(["--strict"])
    assert rc == 0


def test_check_env_strict_port_requires_preferred_port(monkeypatch) -> None:
    monkeypatch.setattr(check_fenrir_env.sys, "version_info", (3, 11, 0))
    monkeypatch.setattr(check_fenrir_env, "_check_imports", lambda: (True, []))
    monkeypatch.setattr(check_fenrir_env, "is_port_open", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(check_fenrir_env, "resolve_service_port", lambda *_args, **_kwargs: 9999)
    rc = check_fenrir_env.main(["--strict", "--strict-port"])
    assert rc == 1
