# ADR-0004 — Constraints eliminate; economics only chooses

**Status:** accepted · **Date:** 2026-08-08

## Context

The natural way to build a decision engine is to score every option and pick the
best total. Residency becomes a weight, latency becomes a weight, cost becomes a
weight, and one function ranks them.

That design has a specific failure: it makes a residency rule tradeable. With a
large enough cost saving, a weighted score will happily recommend exporting
payroll data. It will be *defensible arithmetic* and an indefensible architecture.

## Decision

The rules are split into two kinds, and the code is arranged so they cannot mix.

- **R1–R5 eliminate.** Residency and personal data, delta capability, freshness
  SLO, latency SLO at peak concurrency, share availability. Each removes modes from
  consideration and records why.
- **R7 chooses**, and only among survivors. It never sees an eliminated mode.

`R6` (semantics) is the one deliberate exception, and it is bounded: it may prefer
a share over the cheapest survivor, but only up to a cost premium stated in
`config/policy.yaml` (`max_premium_ratio`). Above that, economics wins and the
register says so. A preference with no stated ceiling is not a policy.

## Consequences

- An object can end at `KEEP_IN_SAP` because nothing survived. That is a real
  outcome the register reports, not an error.
- **Eliminated modes are still priced.** The register shows what the forbidden
  option would have cost, because a constraint nobody has priced is a constraint
  somebody will eventually argue away — usually in a budget meeting, eighteen
  months later, with none of this context in the room.
- Adding a constraint is adding an elimination rule, not adding a weight. This
  keeps the rule set readable top to bottom, which matters more than it sounds: the
  *order* of the rules is the argument, and a scoring function has no order.
