# ADR-0007 — dbt is the consumption layer, and the register generates its bindings

**Status:** accepted · **Date:** 2026-08-16

## Context

`docs/reference-architecture.md` draws a box on the Snowflake side labelled
`raw → integrated → semantic`, and until now nothing in the repo built it. **R9**
— "expose the modelled view, not the raw table" — was the one rule with no
artifact behind it.

The obvious fix is to add a dbt project. But a dbt project sitting next to the
decision engine, unrelated to it, would be exactly the failure this repo exists to
argue against: two boxes on a diagram with nothing joining them. Every SAP-to-cloud
architecture already has a transformation tool in it. That is not the interesting
part.

The interesting part is that **the integration mode and the transformation layer
are not independent**. A replicated object is a table you own. A federated object
is a remote relation you re-read. A shared object is somebody else's file you read
in place. Those are three genuinely different physical bindings with three
different failure modes, three different freshness stories, and three different
bills — and a transformation layer that abstracts over them without knowing which
one it has is a transformation layer that will eventually be surprised.

## Decision

**The register generates the dbt bindings.** `sapbdc dbt-sources` reads the same
decisions `make decide` prints and emits `_sources.yml`, the decided staging model,
and a seed of the register itself. Three consequences follow, and all three are the
point:

1. **A mode is a binding, not a comment.** `SHARE` becomes an `external_location`
   over Parquet, `REPLICATE` a table in an attached warehouse database, `FEDERATE`
   a relation in a read-only attached source. Flip a threshold in
   `config/policy.yaml` and the generated dbt code changes in the diff.
2. **`KEEP_IN_SAP` emits nothing.** An object the engine held back on residency
   grounds has no source to select from, and a model that references it fails to
   compile. R1 stops being a paragraph and becomes a build failure at the place the
   violation would occur.
3. **The mart does not know the mode.** `fct_journal_by_period` refs a generated
   decided model. The three bindings are absorbed in staging. If a mode change
   required editing a mart, the layering would be wrong.

CI gates the generated files the same way it already gates `reports/decisions.md`:
regenerate, `git diff --exit-code`, fail on drift. A policy change that someone
forgot to propagate is caught in review rather than at runtime.

## Why dbt-duckdb, and what that costs in honesty

dbt-duckdb keeps ADR-0001 intact: the whole layer runs on a laptop with no cloud
account. It also happens to be the only adapter that can hold all three bindings in
**one session** — an attached read-only database, a second attached database, and
an external Parquet file — which is what makes the side-by-side comparison
possible at all.

What it is not: **this is not dbt on Snowflake.** The SQL is portable-ish and the
layering is real, but incremental strategies, warehouse sizing, clustering and
micro-partition behaviour — the things that actually decide what a Snowflake dbt
project costs — are not exercised and cannot be inferred from anything here.
`transform/profiles.snowflake.example.yml` declares the target and **is never
executed**; it is there to show the shape, labelled so nobody mistakes it for
evidence (ADR-0002).

dbt is an **optional extra** (`pip install -e ".[dbt]"`, `make dbt`). `make demo`
does not require it, so ADR-0001's "no required external dependency on the default
path" survives.

## Consequences

- The decision engine now has a downstream consumer, which means the register has
  to stay machine-readable. It already was; now that is load-bearing.
- Adding an object to the dbt layer needs a binding entry in
  `config/transform.yaml` — the estate stays data (ADR-0005), including the part of
  it that says where a mode physically lands.
- The staleness test (`assert_only_federation_sees_the_late_change`) couples the
  dbt layer to the simulation's sentinel. If FS-0004's sentinel behaviour changes,
  this test fails — which is correct: it is the same claim, asserted twice.
- `dbt source freshness` is deliberately unused. It reads the wall clock, and
  AGENTS.md rule 7 forbids that in anything committed. Freshness is asserted by
  comparing bindings to each other instead, which is deterministic and is closer to
  the actual argument.

## Alternatives considered

- **A hand-written dbt project.** Faster, and indistinguishable from every other
  dbt demo. It would also have let a source contradict the register silently, which
  is the exact class of drift this repo is about.
- **Generating models, not just sources.** Tempting, and wrong: generated business
  logic is unreviewable. The generator emits *bindings* — the part that is
  mechanically derivable from a decision. The SQL that means something stays
  hand-written.
- **dbt-fal / SQLMesh / plain SQL scripts.** SQLMesh has a better story on
  environments; dbt has the one this repo needs, which is that the reader already
  knows what a `source()` is and can therefore see the claim without learning a
  tool first.
