# ADR-0005 — The estate is data; the rules are code

**Status:** accepted · **Date:** 2026-08-08

## Context

Two things could be configurable: *the landscape* (which objects, how big, how
often queried, under what constraints) and *the reasoning* (what follows from
those facts). Making both configurable produces a rules engine with a DSL nobody
reads. Making neither produces a script that answers exactly one question about
exactly one estate.

## Decision

- **The estate is data.** `config/landscape.yaml`, `config/objects.yaml`,
  `config/policy.yaml`, `config/cost_model.yaml`. Nothing about a particular estate
  is compiled into Python. Pointing this at a different landscape is a YAML edit.
- **The reasoning is code.** `src/sapbdc/rules.py`, read top to bottom, is the
  argument. Its ordering is load-bearing (ADR-0004) and a linear function makes
  that ordering visible in a way a rules table does not.
- **Policy sits between them.** Thresholds a client would genuinely set —
  the full-reload ceiling, the semantics premium, the hybrid drill-down limit —
  live in `policy.yaml`, separately from the cost model, because they are
  governance choices rather than prices.

Loading is strictly validated with Pydantic. A typo in a delta capability, an
unknown source system, a missing consumer profile — each fails loudly at load. A
silent default here would quietly change an architecture decision, which is the
worst possible place for one.

## Consequences

- The interesting review question becomes "do you agree with the *order* of these
  rules?" — which is the question worth having.
- Adapting this to a real estate is: replace `objects.yaml`, replace
  `cost_model.yaml`, adjust `policy.yaml`, re-run. The rules are the part you
  argue with, not the part you configure.
- `decide_object` is one long linear function, deliberately, with a `noqa` for the
  complexity check. Splitting it into per-rule helpers would satisfy a linter and
  hide the sequence that *is* the design.
