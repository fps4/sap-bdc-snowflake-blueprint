# sap-bdc-snowflake-blueprint

A **one-page reference architecture** for SAP source systems → SAP Business Data
Cloud / Datasphere → Snowflake — with the **federate-vs-replicate-vs-share
decision made explicit, priced, and runnable**.

Most SAP-to-cloud reference architectures are a diagram with three arrows and no
argument. This one comes with the argument attached: a catalog of 24 objects
across a mixed SAP estate, an ordered rule set that assigns each one an
integration mode, a cost model that says exactly where federation stops being
cheaper than replication, and a local simulation that executes all three modes so
the claim is demonstrated rather than asserted.

```
SAP sources ──► Business Data Cloud / Datasphere ──►  THE SEAM  ──► Snowflake
S/4HANA · ECC       data products · semantic          share            raw →
BW/4HANA · HCM      models · replication flows        replicate        integrated →
                    remote tables · object store      federate         semantic
                                                      hybrid
                                                      keep in SAP
```

**→ Start with [`docs/reference-architecture.md`](docs/reference-architecture.md).**
That is the page to put on a screen. Everything else in this repo exists to
defend it.

## Honesty statement

This is a **reference architecture with a working decision engine behind it**,
authored **AI-assisted** (agentic workflow; the specs under `docs/` are the design
record and lead the code). What runs is real: the catalog, the rules, the cost
model, the simulation, the reports — `make demo` produces all of it on a laptop
in under a minute.

What is **not** real, and is labelled as such everywhere it appears:

- **No SAP system and no Snowflake account are involved.** DuckDB stands in for
  both sides of the seam. The simulation is honest about which of its measurements
  survive that substitution and which do not — see
  [ADR-0001](docs/design/decisions/0001-local-first-runtime.md).
- **The cost figures are illustrative placeholders shaped like list pricing**, not
  quotes and not a client's rate card. They live in one YAML file precisely so
  they can be replaced with real ones — see
  [ADR-0006](docs/design/decisions/0006-cost-model-provenance.md).
- **The 24-object catalog is invented.** Sizes, delta capability and consumer
  profiles are shaped like a real DACH manufacturing estate; they are not one.
- **The dbt layer runs on DuckDB, and that is not dbt on Snowflake.** The layering
  and the generated bindings are real and tested; incremental strategy, warehouse
  sizing and clustering — the things that actually decide what a Snowflake project
  costs — are not exercised and cannot be inferred from anything here. The
  Snowflake target is declared and never executed — see
  [ADR-0007](docs/design/decisions/0007-dbt-as-the-consumption-layer.md).
- **SAP's integration surface moves quickly.** The mechanisms named here should be
  checked against current SAP documentation before anyone commits a budget.

The durable artifact is the **decision procedure**, not the product matrix and
certainly not the euro figures.

## Why it exists

Two reasons, and they are the same reason.

1. **The seam is where SAP-to-cloud programmes are actually won or lost.** Not the
   ingestion tooling, not the warehouse layering — the per-object question of what
   gets copied, what gets queried in place, what gets shared zero-copy, and what
   never leaves SAP at all. That question is usually answered by default (replicate
   everything) or by preference (whoever is loudest), and both answers cost real
   money for years.
2. **A diagram cannot be challenged; a decision engine can.** Anyone can disagree
   with a box on a slide and get nowhere. Here, disagreement is a pull request
   against `config/policy.yaml` or `config/cost_model.yaml`, and the register
   re-renders with the consequences.

Built alongside preparation for the SAP Business Data Cloud data-architect
certification (**C_BDCDA**) — see
[`docs/c-bdcda-study-map.md`](docs/c-bdcda-study-map.md) for how the exam's domains
map onto the artifacts here.

## Quickstart

```bash
make demo          # decisions + charts + the measured simulation
```

Or step by step:

```bash
make install       # venv + editable install
make decide        # assign a mode to all 24 objects, write reports/
make explain OBJ=ACDOCA
make simulate      # execute all three modes on local synthetic data
make test
```

Requires Python 3.11+. No cloud account, no API key, no Docker.

The transformation layer is an **optional extra**, so the default path above stays
dependency-free ([ADR-0001](docs/design/decisions/0001-local-first-runtime.md)):

```bash
make dbt            # install dbt, simulate, regenerate the bindings, build and test
make dbt-sources    # regenerate the bindings only — run this after any config change
```

## What `make decide` prints

```
CATALOG: 24 objects · target snowflake (eu-central-1)

OBJECT                   SIZE   DELTA    Q/DAY  MODE           €/MONTH  WHY
---------------------------------------------------------------------------
ACDOCA              12,400.0G     cds      900  SHARE            2,679  [R6] Zero-copy share, at a 1.18× premium
BKPF                   420.0G     odp      120  REPLICATE          275  [R7] Cheapest surviving mode
FAGLFLEXT               90.0G     odp       40  FEDERATE            64  [R7] Cheapest surviving mode
MATDOC               4,400.0G     cds      340  HYBRID           1,446  [R8] Replicate the aggregate, federate the detail
PA0002                  12.0G     slt       18  KEEP_IN_SAP          0  [R1] Residency plus personal data
ZFI_ALLOC               88.0G    none      150  FEDERATE           305  [R7] Cheapest surviving mode
...

MIX   SHARE: 9  REPLICATE: 6  FEDERATE: 6  HYBRID: 1  KEEP_IN_SAP: 2
COST  €9,279/month as decided  ·  €27,557/month if everything were replicated  ·  66% avoided
HELD  2 object(s) stay in SAP on constraints, not cost: PA0002, PA0008
```

`make explain OBJ=ACDOCA` prints the full reasoning for one object: every mode
priced, every elimination named, and the crossover frequency.

## The six things to look at

1. **The one page** — [`docs/reference-architecture.md`](docs/reference-architecture.md).
   The diagram, the nine-rule decision ladder, and the crossover formula.
2. **The rules, in order** — [`src/sapbdc/rules.py`](src/sapbdc/rules.py). R1–R5
   eliminate; R7 chooses. Economics never overrules a constraint, and the code is
   arranged so that it *cannot*
   ([ADR-0004](docs/design/decisions/0004-constraints-before-economics.md)).
3. **The crossover** — [`src/sapbdc/econ.py`](src/sapbdc/econ.py). Two straight
   lines and where they meet. Sharing removes the fixed cost and raises the
   marginal one, which is why zero-copy is not a free lunch
   ([ADR-0003](docs/design/decisions/0003-share-as-a-first-class-mode.md)).
4. **The register** — [`reports/decisions.md`](reports/decisions.md). One row per
   object with the reason *in the row*, including what the forbidden options would
   have cost.
5. **The simulation** — [`reports/simulation.md`](reports/simulation.md). All three
   modes executed, and an explicit account of which measurements mean anything on
   a laptop and which do not.
6. **The transformation layer** — [`transform/`](transform/). A dbt project whose
   sources are *generated from the register*: the mode assigned to an object decides
   how it physically binds, `KEEP_IN_SAP` emits no source at all, and the marts never
   name a mode. Start with
   [`stg_journal__decided.sql`](transform/models/staging/stg_journal__decided.sql) —
   it is three lines and it is the whole argument
   ([ADR-0007](docs/design/decisions/0007-dbt-as-the-consumption-layer.md)).

## Layout

| Path | What it is |
|---|---|
| `docs/reference-architecture.md` | **The one page.** |
| `docs/product/` | Functional specs (FS-####) — what each surface must do |
| `docs/design/decisions/` | ADRs — the trade-offs, written down |
| `docs/c-bdcda-study-map.md` | Exam domains → artifacts in this repo |
| `config/` | The landscape, the 24-object catalog, the policy, the cost model |
| `src/sapbdc/` | Catalog, rules, economics, reporting, CLI |
| `src/sapbdc/sim/` | The local three-mode simulation |
| `transform/` | The dbt project — bindings generated from the register (optional extra) |
| `reports/` | Generated: the decision register, the simulation, the charts |

## License

MIT — see [`LICENSE`](LICENSE).
