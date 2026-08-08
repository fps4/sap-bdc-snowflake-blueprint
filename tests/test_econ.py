import pytest

from sapbdc.catalog import Mode, load_catalog
from sapbdc.econ import (
    DAYS_PER_MONTH,
    crossover_queries_per_day,
    federate_economics,
    replicate_economics,
    share_economics,
)


def _object(cat, object_id):
    return next(o for o in cat.objects if o.id == object_id)


def test_at_the_crossover_the_two_modes_cost_the_same():
    """The crossover is only meaningful if it is actually where the lines meet."""
    cat = load_catalog()
    obj = _object(cat, "ACDOCA")
    rep = replicate_economics(obj, cat.costs, schedule_minutes=60)
    fed = federate_economics(obj, cat.costs)
    q = crossover_queries_per_day(rep, fed)
    assert q is not None

    at_rep = rep.fixed_eur_month + rep.variable_eur_per_query * q * DAYS_PER_MONTH
    at_fed = fed.fixed_eur_month + fed.variable_eur_per_query * q * DAYS_PER_MONTH
    assert at_rep == pytest.approx(at_fed, rel=1e-9)


def test_below_the_crossover_federation_is_cheaper_and_above_it_replication_is():
    cat = load_catalog()
    obj = _object(cat, "ACDOCA")
    rep = replicate_economics(obj, cat.costs, schedule_minutes=60)
    fed = federate_economics(obj, cat.costs)
    q = crossover_queries_per_day(rep, fed)

    def cost(e, queries):
        return e.fixed_eur_month + e.variable_eur_per_query * queries * DAYS_PER_MONTH

    assert cost(fed, q * 0.5) < cost(rep, q * 0.5)
    assert cost(rep, q * 2.0) < cost(fed, q * 2.0)


def test_no_delta_capability_moves_the_whole_object_every_cycle():
    """The rule that makes a Z-table without delta expensive rather than merely untidy."""
    cat = load_catalog()
    zfi = _object(cat, "ZFI_ALLOC")
    assert zfi.delta_capability == "none"

    hourly = replicate_economics(zfi, cat.costs, schedule_minutes=60)
    daily = replicate_economics(zfi, cat.costs, schedule_minutes=1440)
    # 24× the cycles means 24× the bytes moved, so a tighter schedule is strictly
    # more expensive when there is no delta to move.
    assert hourly.fixed_eur_month > daily.fixed_eur_month


def test_dominated_mode_reports_no_crossover():
    """Parallel or dominated lines never cross; the model must say so rather than
    invent a number."""
    cat = load_catalog()
    obj = _object(cat, "T001")
    rep = replicate_economics(obj, cat.costs, schedule_minutes=1440)
    assert crossover_queries_per_day(rep, rep) is None


def test_share_has_no_fixed_pipeline_cost():
    cat = load_catalog()
    obj = _object(cat, "ACDOCA")
    rep = replicate_economics(obj, cat.costs, schedule_minutes=60)
    shr = share_economics(obj, cat.costs, share_refresh_minutes=15)
    assert shr.fixed_eur_month < rep.fixed_eur_month
    # ...and buys that with a higher marginal cost. Sharing is not a free lunch;
    # it moves the cost from fixed to variable.
    assert shr.variable_eur_per_query > rep.variable_eur_per_query
    assert shr.mode is Mode.SHARE
