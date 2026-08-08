# C_BDCDA study map — exam domains → artifacts in this repo

The SAP Business Data Cloud data-architect certification (**C_BDCDA**) is
delivered as a **scenario-based assessment**: you reason through a realistic
situation and justify an architecture decision, rather than recalling isolated
facts. That format rewards having *built* a decision procedure, not having read
about one.

This repo was written alongside preparation for it. The table below maps what the
exam asks you to reason about onto the thing here that made that reasoning
concrete. It is a study aid, **not** a syllabus, a question bank, or any claim to
represent SAP's published exam content — check
[SAP's own certification page](https://training.sap.com/certification/) for the
authoritative scope and weighting, which change between versions.

| What the exam asks you to reason about | Where it lives here | What building it forced me to settle |
|---|---|---|
| **Data architecture foundations & modelling** — layering, grain, semantic models | `config/objects.yaml`, the `join_locality` rule (R9) | That "expose the modelled view, not the raw table" is a *modelling* decision with a cost consequence: where the join runs decides what crosses the seam. |
| **Integration patterns** — federation, replication, virtualization, zero-copy sharing | `src/sapbdc/rules.py`, [ADR-0003](design/decisions/0003-share-as-a-first-class-mode.md) | That sharing is a third mode, not a flavour of federation — different executor, different freshness owner, different availability constraint. |
| **SAP Business Data Cloud specifics** — data products, Datasphere, the object store, SAP Databricks, BDC Connect | `docs/reference-architecture.md`, `config/landscape.yaml` | That a data product's *semantics* are the asset, and a replication flow flattens them — so someone rebuilds currency conversion and hierarchies downstream, at a cost that never lands in the pipeline's bill. |
| **Connecting third-party data platforms** — Snowflake in both directions | the `direction: inbound` objects; R5 | That the inbound half is real and usually missing from the diagram: Snowflake as a Datasphere source is a remote table or a replication flow, and never a Delta Share. |
| **Data mesh / data fabric patterns** | `config/policy.yaml` — `share.requires_bdc_data_product` | That "publish a data product" is the mesh's actual unit of work, and the reason zero-copy is unavailable for most custom and legacy objects. |
| **Governance, security, residency** | R1, [ADR-0004](design/decisions/0004-constraints-before-economics.md) | The counter-intuitive one: residency pushes *away* from replication and *toward* federation, because a copy comes to rest and a query result merely passes through — until the data is personal, and then nothing crosses at all. |
| **Data strategy & communicating value to stakeholders** | `reports/decisions.md`, the crossover chart | That the crossover frequency is the artifact a room can actually settle an argument with, because it converts a preference into two checkable numbers. |
| **Framework thinking (DAMA-DMBOK, TOGAF)** | the `docs/` structure: specs, ADRs, a decision register | That a decision register with the reason *in the row* is what makes an architecture reviewable — the same instinct as an ADR, applied per object. |

## How to use this while studying

1. Read [`docs/reference-architecture.md`](reference-architecture.md) — the whole
   argument on one page.
2. Run `make decide`, then `make explain OBJ=<id>` on the objects whose outcome
   surprises you. `ZFI_ALLOC` (a custom table with no delta), `SF_WEB_SESSIONS`
   (huge, rarely queried, inbound) and `PA0002` (nothing may cross) are the three
   that most often change someone's default.
3. Change something in `config/policy.yaml` — the semantics premium, the
   full-reload ceiling — and re-run. Watching which decisions move is worth more
   than reading the register once.
4. Then argue with the rule order in `src/sapbdc/rules.py`. If you can defend a
   different order, you can defend the one it replaced, which is the whole skill
   the scenario format is testing.
