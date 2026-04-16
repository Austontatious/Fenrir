PYTHON ?= python3

.PHONY: run test eval lint smoke

run:
	$(PYTHON) -m fenrir.server list_batteries

test:
	$(PYTHON) -m pytest -q

eval:
	$(PYTHON) evals/runner.py --check

lint:
	$(PYTHON) -m py_compile core/config.py core/prompt_loader.py core/llm.py core/trace.py evals/runner.py
	$(PYTHON) -m py_compile fenrir/server.py scripts/smoke_run.py scripts/validate_battery.py

smoke:
	$(PYTHON) scripts/smoke_run.py
