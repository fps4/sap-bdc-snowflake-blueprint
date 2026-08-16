# FS-0005 — The transformation layer

**Status:** implemented · `src/sapbdc/dbtgen.py`, `transform/`

## Purpose

Build the `raw → integrated → semantic` box that
[`docs/reference-architecture.md`](../reference-architecture.md) draws on the
Snowflake side of the seam, and — the point of the surface — make it **governed by
the decision engine rather than merely adjacent to it**.

Most reference architectures put a transformation tool in a box next to the
integration arrow and leave the two unrelated. Here the register is the input: the
mode assigned to an object decides how that object physically binds in dbt, and a
change to `config/policy.yaml` that flips a mode shows up as a diff in generated
dbt code. That is what turns **R9** ("expose the modelled view, not the raw
table") from an advisory note into an artifact.

## What it does

### 1. Generates the dbt binding from the register

`sapbdc dbt-sources` reads the same decisions `make decide` prints and writes three
generated files. All three carry a "do not edit" header and are regenerated, never
hand-maintained:

| Generated file | What it carries |
|---|---|
| `transform/models/staging/_sources.yml` | one dbt source per catalog object that may cross the seam, grouped by the mode that decided it |
| `transform/models/staging/stg_journal__decided.sql` | selects from the binding the engine chose for `ACDOCA` |
| `transform/seeds/decision_register.csv` | the whole register as data, so dbt tests can assert against it |

The mode decides the physical binding:

| Mode | dbt binding | What the binding costs you |
|---|---|---|
| `REPLICATE` | table in the attached warehouse database | storage at rest and a delta job on every tick |
| `FEDERATE` | relation in the read-only attached source | nothing at rest; the source is re-read per query |
| `SHARE` | `external_location` over the published Parquet | nothing at rest; the producer owns the cadence |
| `HYBRID` | the replicated leg — the aggregate the copy exists for | as `REPLICATE`, with the detail grain federated alongside |
| `KEEP_IN_SAP` | **no source is emitted at all** | the constraint is enforced downstream, not just documented |

### 2. Binds one semantic model to whichever mode won

`stg_journal__replicated`, `stg_journal__federated` and `stg_journal__shared` each
normalise the same SAP column names (`rbukrs`, `gjahr`, `poper`, `racct`, `hsl`)
to business names and stamp the binding they came from. `stg_journal__decided` —
generated — points at the one the engine chose. `fct_journal_by_period` refs the
decided model and **does not know which mode it is reading**.

That is the architectural claim, executable: the mode is a property of the seam,
not of the semantic layer, and flipping it should not touch a mart.

### 3. Tests the seam, not just the SQL

Four singular tests, each asserting something the architecture claims:

- `assert_no_source_is_kept_in_sap` — walks `graph.sources` and fails if any
  declared source names an object the engine held in SAP. **R1 enforced in the
  transformation layer**, where the violation would actually happen.
- `assert_decided_binding_matches_register` — the generated decided model agrees
  with the seeded register. Catches a hand-edited generated file.
- `assert_bindings_agree_on_row_count` — the three bindings carry the same rows.
- `assert_only_federation_sees_the_late_change` — the sentinel row the simulation
  stamps after setup is visible through the federated binding and **not** through
  the replicated copy or the published share. The staleness result from FS-0004,
  restated as a test that fails if it ever stops being true.

## Deliberately not built

- **`dbt source freshness`.** It compares `loaded_at_field` against the wall clock,
  and AGENTS.md rule 7 forbids wall-clock dependence anywhere the output is
  committed. Freshness semantics are instead asserted deterministically, by
  comparing the bindings to each other — which is the actual claim, and stronger.
- **A Snowflake run.** `transform/profiles.snowflake.example.yml` declares the
  target and is never executed (ADR-0007, ADR-0002).
- **Models for all 24 objects.** Only the objects the local simulation actually
  materialises are bound. `config/transform.yaml` names them; the rest appear in
  the register seed and are governed by it.

## Acceptance criteria (EARS)

- **THE SYSTEM SHALL** derive every dbt source from the decision register, so that
  no binding can name an object the engine did not permit across the seam.
- **WHEN** an object's decided mode is `KEEP_IN_SAP`, **THE SYSTEM SHALL** emit no
  source for it, and **SHALL** fail compilation if a model references it anyway.
- **WHEN** an object's decided mode changes, **THE SYSTEM SHALL** produce a
  different `_sources.yml` and `stg_journal__decided.sql`, so the consequence is
  visible as a diff in review.
- **THE SYSTEM SHALL** generate deterministically — no wall clock, no ordering
  dependent on a hash — so that CI can gate the committed files against the code.
- **THE SYSTEM SHALL** remain outside the default path: `make demo` **SHALL NOT**
  require dbt, and the dbt dependency **SHALL** be an optional extra (ADR-0001).
- **THE SYSTEM SHALL** keep the mart layer free of mode-specific SQL, so that a
  mode change touches staging only.
