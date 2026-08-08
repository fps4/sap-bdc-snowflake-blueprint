# ADR-0006 — The cost model is a model, and says so

**Status:** accepted · **Date:** 2026-08-08

## Context

The most quotable output of this repo is a euro figure: *"€9,279/month as decided
against €27,557/month if everything were replicated."* Quotable numbers travel
without their caveats. Within two forwards, an illustrative figure becomes a
benchmark somebody plans against.

The numbers are also unavoidable. A federation-vs-replication decision with no
prices attached is a preference, and preferences are what this repo exists to
replace.

## Decision

Keep the numbers, and make their provenance impossible to lose.

1. **One file.** Every rate lives in `config/cost_model.yaml`. Nothing is hard-coded
   anywhere else.
2. **The disclaimer is in the file, at the top**, not only in the README —
   because the file is what gets copied.
3. **Every generated report repeats it.** The register ends by saying the rates are
   placeholders and inviting their replacement.
4. **The model is transparent, not calibrated.** Each mode is a straight line —
   fixed cost plus a per-query slope — so anyone can check the arithmetic without
   trusting the implementation. Crossovers are computed as line intersections, and
   a test asserts that both modes really do cost the same at the reported crossover.
5. **What matters is which decisions are rate-sensitive.** Replace the rates with a
   real card and re-run: the objects whose mode *changes* are the ones where the
   architecture was never really the deciding factor. That sensitivity is the
   model's actual output; the euro totals are a by-product.

## Consequences

- The headline savings figure is defensible only as *"under these stated
  assumptions"*, and every surface that prints it says so.
- Structural terms are deliberately included even though they are the easiest to
  get wrong — outbound integration metering in whole blocks, the ops cost of
  operating one more pipeline, the consumer compute a replicated copy still incurs.
  Omitting them is what makes "just replicate it all" look cheap on a slide.
- The concurrency penalty on federated latency (ADR-0001) is the single most
  arguable parameter in the repo. It is isolated, named and commented so it can be
  argued with directly rather than discovered in an implementation.
