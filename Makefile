PYTHON ?= python3

.PHONY: run test eval lint smoke validate-artifacts workspace-scope seed-workspace-scope

run:
	$(PYTHON) -m fenrir.server list_batteries

test:
	$(PYTHON) -m pytest -q

eval:
	$(PYTHON) evals/runner.py --check

lint:
	$(PYTHON) -m py_compile core/config.py core/prompt_loader.py core/llm.py core/trace.py evals/runner.py
	$(PYTHON) -m py_compile fenrir/server.py scripts/smoke_run.py scripts/validate_battery.py scripts/validate_artifacts.py scripts/run_gold_slice_eval.py scripts/compare_gold_slice_runs.py scripts/check_workspace_scope.py

smoke:
	$(PYTHON) scripts/smoke_run.py

validate-artifacts:
	$(PYTHON) scripts/validate_artifacts.py --runs-root artifacts/runs

workspace-scope:
	@if [ -z "$(ALLOW)" ]; then echo "Usage: make workspace-scope ALLOW='path1 path2'"; exit 2; fi
	$(PYTHON) scripts/check_workspace_scope.py $(foreach p,$(ALLOW),--allow $(p))

seed-workspace-scope:
	$(PYTHON) scripts/check_workspace_scope.py \
		--allow AGENTS.md \
		--allow Makefile \
		--allow docs \
		--allow scripts \
		--allow tests \
		--allow fenrir/generation \
		--allow fenrir/workspace \
		--allow batteries/frontier_alignment_v1/seeds \
		--allow batteries/frontier_alignment_v1/metadata \
		--allow batteries/frontier_alignment_v1/schemas
