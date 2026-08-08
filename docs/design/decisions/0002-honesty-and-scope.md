# ADR-0002 — Honesty and scope

**Status:** accepted · **Date:** 2026-08-08

## Context

This repo is public build proof. The failure mode for public build proof is not
being wrong — it is being *unfalsifiably impressive*: numbers with no provenance,
a landscape that might be a client's, a "reference architecture" that quietly
implies delivery experience it does not have.

## Decision

Four rules, load-bearing, enforced by review rather than by tooling.

1. **No production, scale or benchmark claims.** No throughput figures, no "serves
   N queries/second", no client names, no implication that this ran anywhere.
2. **Every number is labelled with its provenance.** Cost figures are illustrative
   placeholders (ADR-0006). Latency figures are modelled, not measured (ADR-0001).
   The catalog is invented. Each of these is stated where the number appears, not
   only in a footnote.
3. **The landscape is invented and says so.** It is *shaped* like a DACH
   manufacturing estate because a plausible shape is what makes the decisions worth
   arguing about. It is not any real estate, and no configuration, table name or
   figure is carried over from client work.
4. **The README honesty statement is not softened.** It is the first thing after
   the summary, not the last thing before the licence.

## Consequences

- The repo is less impressive at a glance and more defensible under a question.
  That is the intended trade.
- Anyone can attack the numbers, which is the point: a cost model that cannot be
  attacked is a cost model nobody checked.
- The claim being made is narrow and precise: *this is a decision procedure for
  the SAP↔Snowflake seam, with a runnable implementation.* Not "I have built this
  at scale."
