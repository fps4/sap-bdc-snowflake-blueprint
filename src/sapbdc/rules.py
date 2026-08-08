"""The decision rules — ordered, named, and each one able to say why.

The order is the argument:

    R1  residency & personal data      constraints, not preferences
    R2  delta capability               can you even keep a copy current?
    R3  freshness SLO                  can a schedule meet the promise?
    R4  latency SLO under concurrency  can the source answer in time, at peak?
    R5  share availability             is a zero-copy share on the table at all?
    R6  semantics                      does moving the data lose its meaning?
    R7  economics                      only now, and only among survivors
    R8  hybrid                         split the object when the profile is split
    R9  join locality                  advisory: expose the model, not the table

Rules R1–R5 *eliminate*. Rule R7 *chooses*. That separation is the whole point:
a residency rule is not a number you can trade against a cheaper option, and a
design that lets economics overrule it is a design that will one day be
overruled by a regulator instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import COSTED_MODES, Catalog, DataObject, Mode
from .econ import (
    DAYS_PER_MONTH,
    ModeEconomics,
    crossover_queries_per_day,
    federate_economics,
    replicate_economics,
    share_economics,
)


@dataclass
class Decision:
    """One object's outcome, with the reasoning kept attached to it."""

    object_id: str
    object_name: str
    domain: str
    direction: str
    mode: Mode
    primary_reason: str
    rule_id: str
    eliminated: dict[Mode, str] = field(default_factory=dict)
    economics: dict[Mode, ModeEconomics] = field(default_factory=dict)
    crossover_queries_per_day: float | None = None
    detail_queries_per_day: float = 0.0
    notes: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    @property
    def monthly_eur(self) -> float:
        """Cost of the mode actually chosen.

        HYBRID is priced as its replicate leg *plus* the federated detail traffic —
        a split that hides the second leg's cost is a split that always looks free.
        KEEP_IN_SAP costs nothing at the seam, which is the honest number: the work
        does not disappear, it just stops being an integration.
        """
        if self.mode is Mode.KEEP_IN_SAP:
            return 0.0
        if self.mode is Mode.HYBRID:
            rep = self.economics[Mode.REPLICATE].monthly_eur
            fed = self.economics[Mode.FEDERATE]
            return rep + fed.variable_eur_per_query * self.detail_queries_per_day * DAYS_PER_MONTH
        return self.economics[self.mode].monthly_eur


def _residency_ok(obj: DataObject, target_region: str) -> bool:
    return target_region in obj.governance.residency


def decide_object(obj: DataObject, cat: Catalog) -> Decision:  # noqa: C901 — the rule
    # chain is deliberately linear and readable top to bottom; splitting it would
    # hide the ordering that *is* the design.
    pol = cat.policy
    land = cat.landscape
    target_region = land.target.region

    eliminated: dict[Mode, str] = {}
    notes: list[str] = []
    flags: list[str] = []
    # A latency elimination is specific to *one* consumer profile, so it must not
    # also veto the rarer, less concurrent drill-down leg in R8. A constraint
    # elimination vetoes both.
    federate_blocked_by_constraint = False

    # Cost every mode first, unconditionally — including the modes about to be
    # eliminated. A decision register that cannot say what the forbidden option
    # would have cost cannot show what the constraint is worth, and a constraint
    # nobody has priced is a constraint somebody will eventually argue away.
    schedule = max(
        land.sap.replication_min_schedule_minutes,
        min(land.sap.replication_default_schedule_minutes, obj.consumer.freshness_slo_minutes),
    )
    econ: dict[Mode, ModeEconomics] = {
        Mode.REPLICATE: replicate_economics(obj, cat.costs, schedule),
        Mode.FEDERATE: federate_economics(obj, cat.costs),
        Mode.SHARE: share_economics(obj, cat.costs, land.sap.share_refresh_minutes),
    }
    crossover = crossover_queries_per_day(econ[Mode.REPLICATE], econ[Mode.FEDERATE])

    # ---- R1 · residency and personal data -------------------------------------
    if not _residency_ok(obj, target_region):
        allowed = ", ".join(obj.governance.residency)
        if pol.residency.block_copy_outside_allowed_regions:
            why = (
                f"data may only come to rest in [{allowed}]; the {land.target.platform} "
                f"account is in {target_region}, so any copy at rest is out"
            )
            eliminated[Mode.REPLICATE] = why
            eliminated[Mode.SHARE] = why
        if obj.governance.pii and pol.residency.block_federation_of_pii_outside_allowed_regions:
            federate_blocked_by_constraint = True
            eliminated[Mode.FEDERATE] = (
                "personal data: even a query result crossing the border is an export"
            )
            return Decision(
                object_id=obj.id,
                object_name=obj.name,
                domain=obj.domain,
                direction=obj.direction,
                mode=Mode.KEEP_IN_SAP,
                rule_id="R1",
                primary_reason=(
                    "Residency plus personal data leaves nothing that may cross the seam — "
                    "model and report it inside SAP, and move the question to the data "
                    "instead of the data to the question."
                ),
                eliminated=eliminated,
                economics=econ,
                crossover_queries_per_day=crossover,
                detail_queries_per_day=obj.consumer.detail_queries_per_day,
                notes=notes,
                flags=["residency-restricted", "pii"],
            )
        notes.append(
            "Residency-restricted: federation survives because only non-personal "
            "results cross, never the object itself."
        )
        flags.append("residency-restricted")

    # ---- R2 · delta capability -------------------------------------------------
    if obj.delta_capability == "none" and obj.size_gb > pol.delta.full_reload_ceiling_gb:
        eliminated[Mode.REPLICATE] = (
            f"no delta capability at {obj.size_gb:,.0f} GB — every cycle is a full "
            f"reload, which is the pipeline's whole cost rather than an edge case"
        )
        flags.append("no-delta-at-volume")
    elif obj.delta_capability == "none":
        notes.append(
            f"No delta capability, but only {obj.size_gb:,.2f} GB — a full reload per "
            f"cycle is affordable here. Revisit if it grows past "
            f"{pol.delta.full_reload_ceiling_gb:,.0f} GB."
        )
    if obj.delta_capability == "slt" and pol.delta.flag_slt_on_hot_tables:
        flags.append("slt-trigger-on-source")
        notes.append(
            "Delta is bought with an SLT trigger on a live ERP table — a change to the "
            "source system's runtime, not just to the analytics estate. Needs the "
            "owning team's sign-off, not just the platform team's."
        )

    # ---- R3 · freshness SLO ----------------------------------------------------
    if obj.consumer.freshness_slo_minutes < land.sap.replication_min_schedule_minutes:
        eliminated.setdefault(
            Mode.REPLICATE,
            f"freshness SLO of {obj.consumer.freshness_slo_minutes:.0f} min is tighter "
            f"than the {land.sap.replication_min_schedule_minutes:.0f} min floor a "
            f"replication flow can be scheduled at",
        )
    if obj.consumer.freshness_slo_minutes < land.sap.share_refresh_minutes:
        eliminated.setdefault(
            Mode.SHARE,
            f"freshness SLO of {obj.consumer.freshness_slo_minutes:.0f} min is tighter "
            f"than the share's {land.sap.share_refresh_minutes:.0f} min refresh",
        )

    # ---- R4 · latency SLO, at peak concurrency ---------------------------------
    fed_p95 = econ[Mode.FEDERATE].p95_latency_seconds
    if fed_p95 > obj.consumer.latency_slo_seconds:
        eliminated.setdefault(
            Mode.FEDERATE,
            f"modelled p95 of {fed_p95:.1f}s at {obj.consumer.peak_concurrency} "
            f"concurrent queries misses the {obj.consumer.latency_slo_seconds:.0f}s SLO",
        )

    # ---- R5 · is a share even available? ---------------------------------------
    if pol.share.outbound_only and obj.direction == "inbound":
        eliminated.setdefault(
            Mode.SHARE,
            "inbound direction: Snowflake data reaches SAP as a remote table or a "
            "replication flow, not as a Delta Share",
        )
    elif pol.share.requires_bdc_data_product and not obj.bdc_data_product:
        eliminated.setdefault(
            Mode.SHARE,
            "not covered by an SAP-delivered BDC data product — a zero-copy share "
            "would first have to be built and published, which is a project, not a "
            "connection",
        )

    survivors = [m for m in COSTED_MODES if m not in eliminated]

    if not survivors:
        return Decision(
            object_id=obj.id,
            object_name=obj.name,
            domain=obj.domain,
            direction=obj.direction,
            mode=Mode.KEEP_IN_SAP,
            rule_id="R1-R5",
            primary_reason=(
                "Every mode was eliminated by a constraint. The honest answer is that "
                "this object does not belong on the other side of the seam yet — "
                "change a constraint, or leave it in SAP."
            ),
            eliminated=eliminated,
            economics=econ,
            crossover_queries_per_day=crossover,
            detail_queries_per_day=obj.consumer.detail_queries_per_day,
            notes=notes,
            flags=flags,
        )

    # ---- R7 · economics, among survivors only ----------------------------------
    cheapest = min(survivors, key=lambda m: econ[m].monthly_eur)
    chosen = cheapest
    rule_id = "R7"
    reason = (
        f"Cheapest surviving mode at {obj.consumer.queries_per_day:,.0f} queries/day: "
        f"€{econ[cheapest].monthly_eur:,.0f}/month"
    )

    # ---- R6 · semantics may buy a bounded premium ------------------------------
    if (
        pol.semantics.prefer_share_when_high
        and obj.semantics == "high"
        and Mode.SHARE in survivors
        and cheapest is not Mode.SHARE
    ):
        premium = econ[Mode.SHARE].monthly_eur / max(econ[cheapest].monthly_eur, 1e-9)
        if premium <= pol.semantics.max_premium_ratio:
            chosen = Mode.SHARE
            rule_id = "R6"
            reason = (
                f"Zero-copy share, at a {premium:.2f}× premium over {cheapest.value} — "
                f"accepted because this object carries high business semantics "
                f"(currency, hierarchies, CDS annotations) that a replication flow "
                f"flattens and someone then rebuilds in {land.target.platform}, at a "
                f"cost that never appears in the pipeline's bill"
            )
        else:
            notes.append(
                f"A share would preserve the SAP semantics but costs "
                f"{premium:.2f}× the chosen mode — above the "
                f"{pol.semantics.max_premium_ratio:.2f}× the policy will absorb."
            )

    if chosen is Mode.SHARE and rule_id == "R7":
        reason += " — and zero-copy, so no second copy, no pipeline and no outbound block"

    # ---- R8 · hybrid: split the object when the profile is split ---------------
    if (
        chosen is Mode.REPLICATE
        and obj.consumer.detail_drilldown
        and 0 < obj.consumer.detail_queries_per_day <= pol.hybrid.max_detail_queries_per_day
        and not federate_blocked_by_constraint
    ):
        lat = cat.costs.latency
        detail_p95 = (
            lat.federate_base_seconds
            + lat.federate_seconds_per_gb_scanned * obj.consumer.scan_gb_per_query
        ) * (
            1.0
            + lat.federate_concurrency_penalty_per_query * obj.consumer.detail_peak_concurrency
        )
        if detail_p95 <= obj.consumer.detail_latency_slo_seconds:
            chosen = Mode.HYBRID
            rule_id = "R8"
            reason = (
                f"Replicate the aggregate, federate the detail: the dashboard traffic "
                f"({obj.consumer.queries_per_day:,.0f}/day at "
                f"{obj.consumer.peak_concurrency} concurrent) pays for a copy, the "
                f"{obj.consumer.detail_queries_per_day:,.0f} line-item drill-downs a day "
                f"do not — and at {obj.consumer.detail_peak_concurrency} concurrent a "
                f"federated drill-down answers in a modelled {detail_p95:,.0f}s against a "
                f"{obj.consumer.detail_latency_slo_seconds:,.0f}s allowance, so the full "
                f"grain stays reachable without being copied"
            )
        else:
            notes.append(
                f"A federated drill-down would answer in a modelled {detail_p95:,.0f}s, "
                f"past the {obj.consumer.detail_latency_slo_seconds:,.0f}s allowance — so "
                f"the detail grain has to be replicated with the aggregate, not split off."
            )

    # ---- R9 · join locality, advisory ------------------------------------------
    if obj.consumer.join_locality == "sap" and obj.direction == "outbound":
        notes.append(
            "Joins are predominantly SAP-side: expose the modelled Datasphere view, "
            "not the raw table, so the join runs where the data is and only the "
            "result crosses the seam."
        )
    elif obj.consumer.join_locality == "snowflake" and chosen is Mode.FEDERATE:
        notes.append(
            f"Joins are predominantly {land.target.platform}-side, so every federated "
            "query drags this object across the seam to meet them. Watch the crossover "
            "— this is the mode that degrades first as adoption grows."
        )

    return Decision(
        object_id=obj.id,
        object_name=obj.name,
        domain=obj.domain,
        direction=obj.direction,
        mode=chosen,
        rule_id=rule_id,
        primary_reason=reason,
        eliminated=eliminated,
        economics=econ,
        crossover_queries_per_day=crossover,
        detail_queries_per_day=obj.consumer.detail_queries_per_day,
        notes=notes,
        flags=flags,
    )


def decide_all(cat: Catalog) -> list[Decision]:
    return [decide_object(obj, cat) for obj in cat.objects]
