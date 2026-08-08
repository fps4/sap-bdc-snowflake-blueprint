# ADR-0003 — Zero-copy sharing is a first-class mode, not a variant of federation

**Status:** accepted · **Date:** 2026-08-08

## Context

The question is almost always framed as **federation vs replication**. That framing
was correct when the only two mechanisms were "query it where it is" and "copy it
here". It is no longer correct.

SAP Business Data Cloud exchanges data products with Snowflake over the open
**Delta Sharing** protocol (BDC Connect for Snowflake). The consumer reads
SAP-governed objects in place: no ingest pipeline, no second copy at rest, no
outbound integration metering.

It is tempting to file that under "federation, but better". It is not.

## Decision

`SHARE` is a distinct mode with its own economics, its own freshness semantics and
its own availability constraint.

| | Federation | Share |
|---|---|---|
| Who executes the query | the **source** system, which is also running the business | the **consumer**, on its own compute |
| Freshness | now | the **producer's** refresh cadence |
| Availability | any connected object | only objects covered by an SAP-delivered **data product**, outbound only |
| Failure mode | you slow down the ERP | you depend on someone else's publish schedule |

The simulation demonstrates the freshness difference concretely: after a row is
changed in the source, only federation sees it. The share does not — it waits for
the producer to republish.

**A share is not federation with better economics. It is a copy someone else
operates.** That is a better deal in most cases and a worse one in a few, and it
is a genuinely different dependency either way.

## Consequences

- The engine models three costed modes, plus `HYBRID` and `KEEP_IN_SAP` as
  outcomes. Five outcomes, not two.
- R5 exists solely to ask whether a share is even available. It usually is not,
  for custom and legacy objects — the honest answer being that publishing a data
  product first is a project, not a connection.
- Sharing does **not** dominate. It removes almost all of the fixed cost and
  *raises* the marginal cost, because reading a shared object prunes less well
  than reading a native table. So it wins at moderate frequency on semantically
  rich data and loses to a plain copy on the hottest facts — which is exactly what
  the worked catalog shows, and the opposite of the "zero-copy always wins"
  marketing line.
