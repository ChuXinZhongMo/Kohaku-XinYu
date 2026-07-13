# XinYu developer task runner.
# Works in Git Bash / WSL / Linux. Windows users without `make` can copy the
# commands, or run them via the scripts/ PowerShell helpers.

APP := XinYu-Core/examples/agent-apps/xinyu
PY  := python

.DEFAULT_GOAL := help
.PHONY: help install test test-cov smoke lint lint-critical lint-full fmt typecheck desktop-build desktop-lint check

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime + dev tooling (editable)
	$(PY) -m pip install -e "./XinYu-Core[dev]"

test: ## Run the XinYu app test suite (smoke excluded)
	cd $(APP) && $(PY) -m pytest -q -m "not smoke"

test-cov: ## Run tests with coverage
	cd $(APP) && $(PY) -m pytest -q -m "not smoke" --cov=. --cov-report=term-missing:skip-covered

smoke: ## Run the integration smoke scripts (slow; may need a live env)
	cd $(APP) && $(PY) -m pytest -q -m smoke

lint-critical: ## Ruff critical rules on core + app (matches CI blocking lint)
	ruff check XinYu-Core/src --select F,E9,F63,F7,F82
	ruff check $(APP) --select F,E9,F63,F7,F82 --exclude "**/learning/**,**/runtime/**,**/.venv/**,**/ops/archive/**"

lint-app-critical: ## Alias: critical rules on app only
	ruff check $(APP) --select F,E9,F63,F7,F82 --exclude "**/learning/**,**/runtime/**,**/.venv/**,**/ops/archive/**"

lint: ## Alias: critical lint (pre-push)
	@$(MAKE) lint-critical

lint-full: ## Full expanded ruff (informational; has residual debt)
	ruff check XinYu-Core/src $(APP)

fmt: ## Auto-fix imports/style with ruff
	ruff check --fix XinYu-Core/src $(APP)

typecheck: ## Mypy on the core runtime (gradual)
	mypy XinYu-Core/src/xinyu_runtime

desktop-build: ## Typecheck + build the Electron shell
	cd XinYu_Desktop && npm install && npm run build

desktop-lint: ## Lint the Electron shell
	cd XinYu_Desktop && npm run lint --if-present

check: test lint-critical ## Tests + critical lint (the pre-push gate)
