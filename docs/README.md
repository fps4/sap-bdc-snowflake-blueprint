# Docs

Spec-first: the intent and the decisions precede the code, and stay ahead of it.

## Start here

- [`reference-architecture.md`](reference-architecture.md) — **the one page.** The
  diagram, the nine-rule decision ladder, the five outcomes, the crossover formula.
- [`c-bdcda-study-map.md`](c-bdcda-study-map.md) — how the exam's domains map onto
  the artifacts here.

## Product

| Doc | What it fixes |
|---|---|
| [`product/00-product-intent.md`](product/00-product-intent.md) | What the artifact is and who it is for |
| [`product/FS-0001-catalog-and-landscape.md`](product/FS-0001-catalog-and-landscape.md) | What an estate must declare for a mode to be derivable |
| [`product/FS-0002-decision-engine.md`](product/FS-0002-decision-engine.md) | The rule order and every acceptance criterion on it |
| [`product/FS-0003-cost-model-and-crossover.md`](product/FS-0003-cost-model-and-crossover.md) | The economics and the structural terms that must not be omitted |
| [`product/FS-0004-simulation.md`](product/FS-0004-simulation.md) | What the local simulation proves, and what it does not |

## Decisions

| ADR | The trade-off |
|---|---|
| [0001](design/decisions/0001-local-first-runtime.md) | DuckDB stands in for both sides — runnable by anyone, at the cost of meaningful latency measurement |
| [0002](design/decisions/0002-honesty-and-scope.md) | Less impressive at a glance, more defensible under a question |
| [0003](design/decisions/0003-share-as-a-first-class-mode.md) | Zero-copy sharing is a third mode, not a flavour of federation |
| [0004](design/decisions/0004-constraints-before-economics.md) | Constraints eliminate; economics only chooses among survivors |
| [0005](design/decisions/0005-rules-as-code-config-as-data.md) | The estate is data; the reasoning is code |
| [0006](design/decisions/0006-cost-model-provenance.md) | Keep the numbers; make their provenance impossible to lose |

## Generated

Not edited by hand — regenerate with `make demo`.

- [`../reports/decisions.md`](../reports/decisions.md) — the decision register
- [`../reports/simulation.md`](../reports/simulation.md) — the three modes, measured
- `../reports/crossover.png`, `../reports/mode-mix.png` — the charts
