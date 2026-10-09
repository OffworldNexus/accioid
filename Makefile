# Accioid — developer entry points.
#
# The Home Assistant integration lives in `custom_components/accioid/`.
# Python is managed with `uv`.
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

## -- Home Assistant integration --------------------------------------------

.PHONY: ha-setup
ha-setup: ## Install Python dependencies with uv
	uv sync

.PHONY: ha-fmt
ha-fmt: ## Format the Python integration
	uv run ruff format .

.PHONY: ha-lint
ha-lint: ## Lint + type-check the Python integration
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy custom_components/accioid

.PHONY: ha-test
ha-test: ## Run the Home Assistant tests (unit + BDD)
	uv run pytest

.PHONY: ha-bdd
ha-bdd: ## Run only the BDD scenarios
	uv run pytest -m bdd

.PHONY: ha-dev
ha-dev: ## Start a throwaway local Home Assistant Core (auto-onboarded, dev/dev)
	./scripts/ha-dev.sh up

.PHONY: ha-dev-fg
ha-dev-fg: ## Run the throwaway HA in the foreground (Ctrl+C safe)
	./scripts/ha-dev.sh up-fg

.PHONY: ha-dev-logs
ha-dev-logs: ## Follow the throwaway HA logs
	./scripts/ha-dev.sh logs

.PHONY: ha-dev-restart
ha-dev-restart: ## Restart the throwaway HA
	./scripts/ha-dev.sh restart

.PHONY: ha-dev-stop
ha-dev-stop: ## Stop and remove the throwaway HA
	./scripts/ha-dev.sh down

.PHONY: ha-dev-reset
ha-dev-reset: ## Wipe the throwaway HA config and container
	./scripts/ha-dev.sh reset

## -- Everything -------------------------------------------------------------

.PHONY: lint
lint: ha-lint ## Lint the Python integration

.PHONY: test
test: ha-test ## Run all tests
