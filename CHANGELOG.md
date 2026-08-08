# Changelog

## 0.1.0 — 2026-08-08

First public version.

- **The one page** — `docs/reference-architecture.md`: SAP source systems → SAP
  Business Data Cloud / Datasphere → Snowflake, with the seam drawn as three
  mechanisms and one decision per object.
- **The decision engine** — nine ordered rules over a 24-object catalog of a mixed
  SAP estate (S/4HANA, ECC, BW/4HANA, ERP HCM, plus two inbound Snowflake objects).
  Five outcomes: share, replicate, federate, hybrid, keep in SAP.
- **The economics** — a transparent fixed-plus-slope cost model per mode, modelled
  latency under concurrency, and the crossover frequency at which replication
  overtakes federation.
- **The simulation** — all three modes executed locally on DuckDB against the same
  synthetic source, measuring bytes at rest, the recurring delta run, and which
  modes see a change posted after setup.
- **The reports** — a decision register with the reason in every row, and two
  charts.
- Specs (FS-0001…FS-0004) and six ADRs; CI runs lint, the engine, the simulation,
  the tests, and a staleness gate on the committed register.
