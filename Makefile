.DEFAULT_GOAL := help
PY ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

$(BIN)/python:
	$(PY) -m venv $(VENV)
	$(BIN)/python -m pip install -U pip

.PHONY: install
install: $(BIN)/python ## Create the venv and editable-install with dev extras
	$(BIN)/pip install -e ".[dev]"

.PHONY: decide
decide: install ## Assign an integration mode to every object; write reports/
	$(BIN)/python -m sapbdc decide

.PHONY: explain
explain: install ## Explain one object: make explain OBJ=ACDOCA
	$(BIN)/python -m sapbdc explain $(or $(OBJ),ACDOCA)

.PHONY: simulate
simulate: install ## Execute all three modes on local synthetic data
	$(BIN)/python -m sapbdc simulate

.PHONY: demo
demo: decide simulate ## The whole thing: decisions, charts, and the measured simulation
	@echo
	@echo "reports/decisions.md   — the decision register"
	@echo "reports/simulation.md  — the three modes, measured"
	@echo "reports/crossover.png  — where replication overtakes federation"
	@echo "docs/reference-architecture.md — the one page to put on screen"

# ---- the transformation layer (optional; ADR-0001 keeps it off the default path) --

.PHONY: install-dbt
install-dbt: $(BIN)/python ## Install the optional dbt extra
	$(BIN)/pip install -e ".[dev,dbt]"

.PHONY: dbt-sources
dbt-sources: install ## Regenerate the dbt bindings from the decision register
	$(BIN)/python -m sapbdc dbt-sources

.PHONY: dbt
dbt: install-dbt simulate dbt-sources ## Build and test the dbt layer on the simulation's output
	cd transform && ../$(BIN)/dbt build --profiles-dir .

.PHONY: dbt-docs
dbt-docs: install-dbt dbt-sources ## Generate the dbt docs site into transform/target
	cd transform && ../$(BIN)/dbt docs generate --profiles-dir .

.PHONY: test
test: install ## Run the test suite
	$(BIN)/pytest -q

.PHONY: lint
lint: install ## Lint
	$(BIN)/ruff check .

.PHONY: clean
clean: ## Remove generated data and reports
	rm -rf data/*.duckdb data/share reports/*.png reports/*.md \
	       transform/target transform/dbt_packages transform/logs
