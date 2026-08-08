# FS-0003 — Cost model and crossover

**Status:** implemented · `src/sapbdc/econ.py`, `config/cost_model.yaml`

## Purpose

Give every mode a monthly cost and a modelled latency, and compute the query
frequency at which two modes cost the same.

## The shape

Each mode is a straight line: a monthly **fixed** cost plus a **per-query** slope.

| Mode | Fixed | Per query |
|---|---|---|
| REPLICATE | amortised initial load + delta movement + target storage + outbound integration blocks + pipeline ops | consumer compute on a native table |
| FEDERATE | remote-table ops | source compute + egress |
| SHARE | share ops | consumer compute on a shared object (higher per GB than a native table) |

Two lines cross where `(F_a − F_b) / ((v_b − v_a) × 30)` is positive; parallel or
dominated lines have no crossover and the model reports none rather than inventing
one.

## Structural terms that must not be omitted

- **Outbound integration is metered in whole blocks.** A month that moves 1.1 GB
  over a 1 GB block costs two blocks.
- **No delta capability means the whole object moves every cycle**, so a tighter
  schedule is strictly more expensive — the opposite of the intuition that a
  tighter schedule is merely "more current".
- **A replicated copy still costs consumer compute to query.** Omitting this is
  what makes replication look like a one-off.
- **Federated latency degrades with concurrency.** The penalty term is the reason a
  federated query passes its SLO in a demo and fails at month-end close, and is the
  most arguable parameter in the repo (ADR-0001).

## Acceptance criteria (EARS)

- **THE SYSTEM SHALL** compute cost from `config/cost_model.yaml` only — no rate
  hard-coded elsewhere.
- **WHEN** a crossover is reported, **THE SYSTEM SHALL** ensure both modes cost the
  same at that frequency (asserted by test).
- **WHEN** two modes' lines never cross at a non-negative frequency, **THE SYSTEM
  SHALL** report no crossover.
- **THE SYSTEM SHALL** state in every generated report that the rates are
  illustrative placeholders (ADR-0006).
