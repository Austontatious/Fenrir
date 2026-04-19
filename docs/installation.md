# Installation

## Goal

Set up Fenrir as a local service with a setup-first web UI.

Primary path:

1. install dependencies,
2. initialize local config,
3. start service,
4. open web UI and configure model endpoint.

## Prerequisites

- Python 3.11+
- Network access to your target model endpoint (unless using mock provider)

## One-Step Setup

From repo root:

```bash
python3 scripts/install_fenrir.py
```

What it does:

- installs dependencies (`pip install -e .[dev]`) unless `--skip-install` is used,
- creates `.env` from `.env.example` when missing,
- preserves existing `.fenrir/local_config.json` by default (creates if missing),
- resolves a usable local service port (default starts at `8765`).

Local state contract:

- schema version: `fenrir.local_state.v1`
- missing-version legacy state is migrated automatically
- malformed/unsupported state is repaired with defaults and a state notice
- writes are atomic (temp file + replace) to reduce partial-write corruption risk

To explicitly reset local state to defaults during install:

```bash
python3 scripts/install_fenrir.py --overwrite-state
```

## Preserve vs Refreshed Fields

Default install path (`--overwrite-state` not set):

- preserves user-owned settings from local state:
  - provider/base URL/API key/model/timeout
  - battery id and conditions
  - MCP enabled/host/port
- refreshes resolved runtime host/port from the current install invocation

Explicit reset path (`--overwrite-state`):

- resets user-owned settings to defaults from env/config
- then applies resolved runtime host/port from the current install invocation

## Start Immediately After Install

```bash
python3 scripts/install_fenrir.py --start
```

When `--start` is used, trust the runtime URL printed by startup logs (`start_fenrir.py` / service output) as the source of truth.

## Separate Start

```bash
python3 scripts/start_fenrir.py
```

Then open:

- `http://127.0.0.1:8765/` (or printed fallback URL)

## Environment Check

```bash
python3 scripts/check_fenrir_env.py
```

Use strict failure mode for CI/local gating:

```bash
python3 scripts/check_fenrir_env.py --strict
```

To require the exact preferred port in env check:

```bash
python3 scripts/check_fenrir_env.py --strict --strict-port
```

## Common Options

Installer:

```bash
python3 scripts/install_fenrir.py --skip-install --host 127.0.0.1 --port 8800
```

Starter with strict port behavior:

```bash
python3 scripts/start_fenrir.py --host 127.0.0.1 --port 8765 --strict-port
```

If `--strict-port` is not set, Fenrir scans upward for an open port.
