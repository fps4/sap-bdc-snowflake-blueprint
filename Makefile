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

.PHONY: test
test: install ## Run the test suite
	$(BIN)/pytest -q

.PHONY: lint
lint: install ## Lint
	$(BIN)/ruff check .

.PHONY: clean
clean: ## Remove generated data and reports
	rm -rf data/*.duckdb data/share reports/*.png reports/*.md
