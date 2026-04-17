from __future__ import annotations

import json
from pathlib import Path
import threading
import urllib.request

from fenrir.config import FenrirConfig
from fenrir.local_service import FenrirHTTPServer, FenrirLocalService


def test_local_service_health_and_mock_connection(tmp_path: Path) -> None:
    cfg = FenrirConfig.from_env()
    state_path = tmp_path / "state.json"
    service = FenrirLocalService(config=cfg, state_path=state_path)

    service.update_config({"provider": "mock", "api_key": ""})
    result = service.test_connection()

    assert result["status"] == "ok"
    assert result["provider"] == "mock"


def test_http_health_endpoint(tmp_path: Path) -> None:
    cfg = FenrirConfig.from_env()
    state_path = tmp_path / "state.json"
    app = FenrirLocalService(config=cfg, state_path=state_path)

    server = FenrirHTTPServer(("127.0.0.1", 0), app)
    port = int(server.server_address[1])

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["status"] == "ok"
        assert payload["service"] == "fenrir_local_service"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
