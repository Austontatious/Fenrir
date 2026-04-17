# Local Service

## Runtime Shape

Fenrir runs as a local HTTP service with a setup-first UI.

Default:

- host: `127.0.0.1`
- port: `8765`
- URL: `http://127.0.0.1:8765`

If the requested port is busy, the starter scans upward (bounded by `FENRIR_SERVICE_PORT_SCAN_LIMIT`) unless `--strict-port` is used.

## Start Commands

```bash
python3 scripts/start_fenrir.py
```

or:

```bash
python3 -m fenrir.server serve-local
```

## Health and Core Endpoints

- `GET /healthz`
- `GET /api/status`
- `GET /api/config`
- `POST /api/config`
- `POST /api/test-connection`
- `POST /api/run-evaluation`
- `GET /api/readout/latest`
- `GET /api/readout/llm-export`

## Configuration Sources

Fenrir uses:

- environment defaults from `.env` / env vars,
- persisted local state at `.fenrir/local_config.json`.

Relevant environment variables:

- `FENRIR_SERVICE_HOST`
- `FENRIR_SERVICE_PORT`
- `FENRIR_SERVICE_PORT_SCAN_LIMIT`
- `FENRIR_LOCAL_CONFIG_PATH`
- `FENRIR_LOCAL_STATE_DIR`

Model endpoint defaults:

- `FENRIR_OPENAI_BASE_URL`
- `FENRIR_OPENAI_MODEL`
- `FENRIR_OPENAI_API_KEY`
- `FENRIR_OPENAI_TIMEOUT_SECONDS`

## Logging

Startup logging prints:

- resolved service URL,
- setup UI URL,
- health endpoint,
- optional MCP mode status.

## Optional MCP Exposure

Fenrir's MCP-facing surface remains optional and secondary.

- Primary path: direct endpoint setup via local UI.
- Optional interop path: MCP-style tool facade commands via `fenrir-server tool ...`.
- UI surfaces MCP as integration info, not as the main setup path.
