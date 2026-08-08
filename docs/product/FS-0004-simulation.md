# FS-0004 — The local simulation

**Status:** implemented · `src/sapbdc/sim/`

## Purpose

Execute all three costed modes against the same data so the architecture's claims
are demonstrated rather than asserted — and be explicit about which of the
resulting measurements mean anything (ADR-0001).

## What it does

1. Generates a deterministic synthetic SAP-shaped source in DuckDB: a
   universal-journal fact with company code, fiscal year/period, account and
   amount, plus material and customer master, each row carrying a change timestamp.
2. Runs each mode against a pristine copy of that source:
   - **REPLICATE** — initial load to a watermark, then a delta upsert (delete then
     insert by key, because a changed document is an update, not an append).
   - **FEDERATE** — views over the attached source; nothing persisted.
   - **SHARE** — the producer publishes Parquet once; the consumer reads it in place.
3. After each mode is set up, changes one row in the source and asks the mode
   whether it noticed.

## What it proves, and what it does not

**Proves** — bytes at rest in the warehouse; whether a recurring job exists and
what it costs to run; which modes can see a change posted a second ago.

**Does not prove** — query latency. One machine, one storage engine: the three
modes come out nearly identical by construction. The generated report prints the
timings labelled *ignore*, rather than omitting them.

## Acceptance criteria (EARS)

- **THE SYSTEM SHALL** rebuild the source before each mode, so that the staleness
  result reflects that mode alone.
- **THE SYSTEM SHALL** generate data deterministically — no wall-clock or random
  seeding — so two runs on two machines differ only in timings.
- **THE SYSTEM SHALL** report, for each mode: setup time, recurring time, bytes at
  rest in the warehouse, bytes published, and whether a post-setup source change is
  visible.
- **THE SYSTEM SHALL** state in the generated report which measurements survive the
  DuckDB substitution and which do not.
- **THE SYSTEM SHALL** run on a laptop in under a minute with no external service.
