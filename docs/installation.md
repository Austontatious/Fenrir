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
- initializes local config at `.fenrir/local_config.json`,
- resolves a usable local service port (default starts at `8765`).

## Start Immediately After Install

```bash
python3 scripts/install_fenrir.py --start
```

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
