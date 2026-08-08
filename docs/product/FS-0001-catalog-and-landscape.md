# FS-0001 — Catalog and landscape

**Status:** implemented · `config/`, `src/sapbdc/catalog.py`

## Purpose

Describe an SAP estate and its Snowflake target precisely enough that an
integration mode can be *derived* rather than chosen.

## What an object must declare

| Group | Fields | Why the decision needs it |
|---|---|---|
| Identity | `id`, `name`, `domain`, `source`, `direction` | Direction decides whether sharing is even available (R5) |
| Physics | `size_gb`, `daily_delta_gb`, `delta_capability` | No delta above the ceiling ⇒ no replication (R2) |
| Semantics | `bdc_data_product`, `semantics` | A share is only possible for a data product (R5); high semantics can buy a bounded premium (R6) |
| Consumer | `queries_per_day`, `peak_concurrency`, `scan_gb_per_query`, `result_gb_per_query`, `latency_slo_seconds`, `freshness_slo_minutes`, `join_locality`, and the separate drill-down profile | Everything in R3, R4, R7, R8, R9 |
| Governance | `residency`, `pii`, `classification` | R1 |

The drill-down profile (`detail_queries_per_day`, `detail_peak_concurrency`,
`detail_latency_slo_seconds`) is separate on purpose: a dashboard and a line-item
drill-down are two workloads with different concurrency and different patience,
and collapsing them into one profile is what makes a hybrid split look like a
hedge instead of a decision.

## Acceptance criteria (EARS)

- **WHEN** the catalog is loaded, **THE SYSTEM SHALL** validate every object
  against the typed schema and fail loudly on an unknown field value.
- **WHEN** an object names a source system absent from the landscape, **THE SYSTEM
  SHALL** raise rather than default.
- **WHILE** any object is missing a consumer profile, **THE SYSTEM SHALL NOT**
  produce a decision for the catalog.
- **THE SYSTEM SHALL** treat every configuration value as data — no estate fact
  compiled into code (ADR-0005).
