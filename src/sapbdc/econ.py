"""The economics: monthly cost per mode, modelled p95 latency, and the crossover.

The shape of the argument, which is the part that matters more than the numbers:

* **Replication** is mostly *fixed* cost — a delta pipeline, a second copy at
  rest, outbound integration blocks, and an object you now operate. Its marginal
  cost per query is close to zero.
* **Federation** is mostly *variable* cost — source compute and egress, paid on
  every query. Its fixed cost is close to zero.
* **Sharing** (zero-copy, Delta Sharing) removes the fixed side without adding
  the variable side: no pipeline, no second copy, no outbound block, and the
  consumer pays only for reading.

Two straight lines that cross. Below the crossover query frequency, federate;
above it, replicate. Everyone in the room can argue about the slope — which is
exactly what you want them arguing about, instead of about preferences.
"""

from __future__ import annotations

from dataclasses import dataclass

from .catalog import CostModel, DataObject, Mode

DAYS_PER_MONTH = 30.0


@dataclass(frozen=True)
class ModeEconomics:
    """One mode's cost and latency for one object, split fixed vs variable."""

    mode: Mode
    fixed_eur_month: float
    variable_eur_per_query: float
    monthly_eur: float
    p95_latency_seconds: float
    freshness_minutes: float

    @property
    def annual_eur(self) -> float:
        return self.monthly_eur * 12.0


def replicate_economics(
    obj: DataObject, costs: CostModel, schedule_minutes: float
) -> ModeEconomics:
    """Cost of holding a second copy, kept current on a schedule."""
    c = costs.replicate
    monthly_delta_gb = obj.daily_delta_gb * DAYS_PER_MONTH

    # No delta capability means every cycle moves the whole object, not the change.
    if obj.delta_capability == "none":
        cycles_per_month = DAYS_PER_MONTH * (24 * 60 / schedule_minutes)
        monthly_moved_gb = obj.size_gb * cycles_per_month
    else:
        monthly_moved_gb = monthly_delta_gb

    initial = (obj.size_gb * c.initial_load_eur_per_gb) / c.amortise_initial_load_months
    movement = monthly_moved_gb * c.delta_move_eur_per_gb
    storage = obj.size_gb * c.target_storage_eur_per_gb_month
    # Outbound integration is metered in whole blocks — a 21 GB month costs two.
    blocks = -(-monthly_moved_gb // c.outbound_block_gb_per_month)  # ceil
    licence = blocks * c.outbound_block_eur_per_month

    fixed = initial + movement + storage + licence + c.ops_eur_per_object_month
    per_query = obj.consumer.scan_gb_per_query * c.consumer_compute_eur_per_gb_scanned

    lat = costs.latency
    p95 = lat.replicate_base_seconds + lat.replicate_seconds_per_gb_scanned * (
        obj.consumer.scan_gb_per_query
    )
    return ModeEconomics(
        mode=Mode.REPLICATE,
        fixed_eur_month=fixed,
        variable_eur_per_query=per_query,
        monthly_eur=fixed + per_query * obj.consumer.queries_per_day * DAYS_PER_MONTH,
        p95_latency_seconds=p95,
        # A replicated object is exactly as fresh as its last successful run.
        freshness_minutes=schedule_minutes,
    )


def federate_economics(obj: DataObject, costs: CostModel) -> ModeEconomics:
    """Cost of leaving the data where it is and paying per question asked."""
    c = costs.federate
    per_query = (
        obj.consumer.scan_gb_per_query * c.source_compute_eur_per_gb_scanned
        + obj.consumer.result_gb_per_query * c.egress_eur_per_gb
    )
    monthly = c.ops_eur_per_object_month + per_query * obj.consumer.queries_per_day * DAYS_PER_MONTH

    lat = costs.latency
    base = lat.federate_base_seconds + lat.federate_seconds_per_gb_scanned * (
        obj.consumer.scan_gb_per_query
    )
    # Federation executes on the source system, which is also running the business.
    # Concurrency is the term that makes a federated query pass its SLO in a demo
    # and fail it at month-end close.
    p95 = base * (
        1.0 + lat.federate_concurrency_penalty_per_query * obj.consumer.peak_concurrency
    )
    return ModeEconomics(
        mode=Mode.FEDERATE,
        fixed_eur_month=c.ops_eur_per_object_month,
        variable_eur_per_query=per_query,
        monthly_eur=monthly,
        p95_latency_seconds=p95,
        freshness_minutes=0.0,
    )


def share_economics(
    obj: DataObject, costs: CostModel, share_refresh_minutes: float
) -> ModeEconomics:
    """Zero-copy: no pipeline, no second copy, no outbound block."""
    c = costs.share
    per_query = obj.consumer.scan_gb_per_query * c.consumer_compute_eur_per_gb_scanned
    monthly = c.ops_eur_per_object_month + per_query * obj.consumer.queries_per_day * DAYS_PER_MONTH

    lat = costs.latency
    p95 = lat.share_base_seconds + lat.share_seconds_per_gb_scanned * (
        obj.consumer.scan_gb_per_query
    )
    return ModeEconomics(
        mode=Mode.SHARE,
        fixed_eur_month=c.ops_eur_per_object_month,
        variable_eur_per_query=per_query,
        monthly_eur=monthly,
        p95_latency_seconds=p95,
        freshness_minutes=share_refresh_minutes,
    )


def crossover_queries_per_day(high_fixed: ModeEconomics, low_fixed: ModeEconomics) -> float | None:
    """Query frequency at which two modes cost the same.

    Each mode is a straight line — fixed cost plus a per-query slope — so this is
    just where they intersect. ``None`` when they never do: parallel slopes, or an
    intersection at a negative frequency, which is the model's way of saying one
    mode dominates the other outright and there is no trade-off to discuss.
    """
    d_fixed = high_fixed.fixed_eur_month - low_fixed.fixed_eur_month
    d_slope = low_fixed.variable_eur_per_query - high_fixed.variable_eur_per_query
    if d_slope <= 0:
        return None
    q = d_fixed / (d_slope * DAYS_PER_MONTH)
    return q if q >= 0 else None


def cost_curve(
    econ: ModeEconomics, queries_per_day: list[float]
) -> list[float]:
    """Monthly cost of one mode across a sweep of query frequencies (for the chart)."""
    return [
        econ.fixed_eur_month + econ.variable_eur_per_query * q * DAYS_PER_MONTH
        for q in queries_per_day
    ]
