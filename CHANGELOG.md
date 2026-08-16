# Changelog

## Unreleased

- **The transformation layer** — `transform/`, a dbt project on DuckDB that builds
  the `raw → integrated → semantic` box the reference architecture draws. Its
  bindings are **generated from the decision register** (`make dbt-sources`): the
  mode assigned to an object decides how that object physically binds, `KEEP_IN_SAP`
  emits no source at all, and the marts never name a mode.
- **Four singular tests that assert the architecture, not the SQL** — no source may
  name an object held in SAP (R1, enforced as a build failure); the generated
  bindings must agree with the register; the three bindings must carry the same
  rows; and only federation may see a change posted after setup.
- **CI/CD** — the workflow gains a Python matrix, least-privilege permissions,
  run-cancelling concurrency, a `transform` job with a staleness gate on the
  generated dbt files, a `publish` job that renders the artifact set to GitHub Pages
  (opt-in via `ENABLE_PAGES`), and a tagged `release` job.
- FS-0005 and ADR-0007. dbt is an **optional extra** — `make demo` still needs
  nothing but Python (ADR-0001).

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
