from __future__ import annotations

from pathlib import Path
import socket

from fenrir.config import FenrirConfig
from fenrir.local_runtime import (
    LocalServiceState,
    default_local_state,
    load_local_state,
    resolve_service_port,
    save_local_state,
)


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
