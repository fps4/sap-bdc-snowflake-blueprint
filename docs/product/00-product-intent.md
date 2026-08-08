# Product intent

## The artifact

**One page you can put on a screen** — SAP source systems → SAP Business Data
Cloud / Datasphere → Snowflake — with the federation-vs-replication-vs-sharing
decision made explicit and justified, and a runnable implementation behind it that
survives the follow-up question.

## The problem it addresses

At the SAP↔cloud seam, the per-object question — copy it, query it in place, share
it zero-copy, or leave it in SAP — is normally answered one of two ways:

- **By default.** Replicate everything. Nobody has to decide anything, and the
  estate accumulates pipelines, duplicate storage and outbound metering for years.
- **By preference.** Whoever argues hardest. The argument is unresolvable because
  neither side has priced their position.

Both produce architectures nobody can defend eighteen months later, when the
person who chose has moved on and only the bill remains.

## What "done" looks like

1. A reader who spends **two minutes** sees the diagram, the five outcomes and the
   crossover formula, and can restate the argument.
2. A reader who spends **twenty minutes** runs `make demo`, disagrees with a
   specific number, changes it in `config/`, re-runs, and sees which decisions move.
3. A reader who spends **an hour** attacks the *order* of the rules — which is the
   only part that is really an architecture opinion.

## Audience

Technical screens and architecture conversations for SAP data-architecture and
data-platform roles. Secondarily, anyone actually facing this seam who wants a
starting decision procedure rather than a starting diagram.

## Non-goals

- Not a migration tool, an ingestion framework, or anything that touches a real
  SAP or Snowflake system (ADR-0001).
- Not a pricing calculator. The rates are placeholders; the *sensitivity* is the
  output (ADR-0006).
- Not a claim of delivery at scale. See the README honesty statement and ADR-0002.
