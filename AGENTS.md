# AGENTS.md — how this repo is built and worked

Spec-first and AI-assisted. Read this before changing anything.

## Working rules

1. **Specs lead code.** Every surface has a functional spec under `docs/product/`
   (FS-####) with EARS acceptance criteria, and a decision under
   `docs/design/decisions/` (ADR-####). Change the spec first, then the code.
2. **Honesty rule (ADR-0002).** No production, scale or benchmark claims. No client
   names or carried-over configuration. The README honesty statement is
   load-bearing — do not soften it.
3. **Local-first (ADR-0001).** The default path runs with no cloud account, no API
   key and no Docker. Do not add a required external dependency.
4. **Constraints eliminate; economics chooses (ADR-0004).** Never turn a constraint
   into a weight. New constraints are elimination rules in R1–R5, not terms in the
   cost function.
5. **The estate is data (ADR-0005).** No estate fact — a size, a rate, a threshold —
   is hard-coded. It goes in `config/`.
6. **Numbers carry their provenance (ADR-0006).** Any new figure states where it
   came from, in the file where it lives *and* in anything that prints it.
7. **Determinism.** No wall-clock or randomness in the catalog, the rules, or the
   data generator. Two runs must differ only in timings.
8. **`decide_object` stays one linear function.** Its ordering *is* the design.
   Splitting it into per-rule helpers would satisfy a linter and hide the argument.

## Layout

- `docs/` — the one page, specs, ADRs (the design record)
- `config/` — landscape, objects, policy, cost model
- `src/sapbdc/` — `catalog.py`, `rules.py`, `econ.py`, `report.py`, `cli.py`
- `src/sapbdc/sim/` — the local three-mode simulation
- `tests/` — one test per rule, so a change to the rule set has to be deliberate
- `reports/` — generated; never edited by hand

## Definition of done for any change

- Matching spec updated; an ADR added if a real trade-off was made.
- `make lint`, `make test` and `make demo` green locally; CI green.
- `reports/decisions.md` regenerated if the decisions moved, and any figure quoted
  in `README.md` or `docs/reference-architecture.md` updated to match.
- No new required external dependency on the default path.
