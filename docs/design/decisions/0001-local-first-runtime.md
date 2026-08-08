# ADR-0001 — Local-first runtime: DuckDB stands in for both sides of the seam

**Status:** accepted · **Date:** 2026-08-08

## Context

The artifact this repo exists to defend is a decision procedure for moving data
between SAP Business Data Cloud / Datasphere and Snowflake. The obvious way to
demonstrate it is to run it against a real SAP tenant and a real Snowflake
account.

That path costs money, needs entitlements most readers do not have, and — worse —
makes the repo unrunnable for anyone evaluating it. A demonstration nobody can
execute is a screenshot.

## Decision

The default and only path runs locally on DuckDB, with **no cloud account, no API
key and no Docker**. An attached read-only DuckDB database plays the SAP source,
the working database plays Snowflake, and a Parquet file on disk plays the
Delta-Sharing object.

The simulation states, in its own generated output, which of its measurements
survive that substitution:

- **Survives** — bytes at rest in the warehouse; whether a recurring job exists at
  all and what it costs to run; whether a mode can see a change posted a second
  ago.
- **Does not survive** — query latency. On one machine with one storage engine the
  three modes come out nearly identical *by construction*. The real federation
  penalty is a network hop into a system that is also running the business, and no
  laptop reproduces it.

The report prints the query times anyway, labelled "ignore", rather than hiding
them. A measurement quietly omitted is a measurement a reader will assume was
favourable.

## Consequences

- Anyone can `make demo` in under a minute and see the whole argument.
- Latency claims in the cost model are **modelled**, not measured, and are marked
  as such in `config/cost_model.yaml`. The concurrency penalty term in particular
  is a modelling assumption about how a federated query behaves on a busy ERP —
  the single most arguable number in the repo, and deliberately isolated in one
  file so it can be argued with.
- Running this against a real tenant would be a genuine follow-up, and would
  mostly serve to calibrate the latency model. The decision procedure would not
  change.

## Alternatives considered

- **Postgres for the source, Snowflake trial for the target.** Closer to the real
  thing; gated on a trial account with an expiry, which puts a clock on the repo's
  runnability.
- **No simulation at all — model everything.** Cheaper and more honest about its
  limits, but then nothing in the repo is executed, and the whole point was to be
  the version of this diagram that is not slideware.
