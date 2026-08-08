# FS-0002 — The decision engine

**Status:** implemented · `src/sapbdc/rules.py`

## Purpose

Assign every catalog object exactly one integration mode, with the reasoning
attached, deterministically.

## The rule order

R1 residency & personal data · R2 delta capability · R3 freshness SLO · R4 latency
SLO at peak concurrency · R5 share availability · R6 semantics · R7 economics ·
R8 hybrid · R9 join locality (advisory).

R1–R5 eliminate. R7 chooses among survivors. See
[ADR-0004](../design/decisions/0004-constraints-before-economics.md) for why the
split is structural rather than stylistic.

## Outcomes

`SHARE` · `REPLICATE` · `FEDERATE` · `HYBRID` · `KEEP_IN_SAP`.

## Acceptance criteria (EARS)

- **THE SYSTEM SHALL** produce exactly one decision per object, each carrying the
  deciding rule id and a reason in plain language.
- **THE SYSTEM SHALL NOT** select a mode that any rule eliminated.
- **WHEN** every mode has been eliminated, **THE SYSTEM SHALL** return
  `KEEP_IN_SAP` and name the constraints, rather than returning an error or a
  least-bad option.
- **WHEN** a mode is eliminated, **THE SYSTEM SHALL** still report what that mode
  would have cost.
- **WHEN** an object's residency excludes the target region **AND** it carries
  personal data, **THE SYSTEM SHALL** return `KEEP_IN_SAP`.
- **WHEN** an object's residency excludes the target region **AND** it carries no
  personal data, **THE SYSTEM SHALL** eliminate `REPLICATE` and `SHARE` but leave
  `FEDERATE` standing.
- **WHEN** an object has no delta capability **AND** exceeds the policy's
  full-reload ceiling, **THE SYSTEM SHALL** eliminate `REPLICATE`.
- **WHEN** the modelled federated p95 at peak concurrency exceeds the latency SLO,
  **THE SYSTEM SHALL** eliminate `FEDERATE`.
- **WHEN** an object is not covered by a BDC data product, **OR** its direction is
  inbound, **THE SYSTEM SHALL** eliminate `SHARE`.
- **WHERE** an object's semantics are high **AND** a share survives, **THE SYSTEM
  SHALL** prefer `SHARE` only while its cost premium is within the policy ratio,
  and **SHALL** record the premium either way.
- **WHERE** a replicated object has a rare drill-down that a federated query could
  serve inside its own latency allowance, **THE SYSTEM SHALL** return `HYBRID` and
  price both legs.
- **THE SYSTEM SHALL** be deterministic: the same catalog yields the same
  decisions.
