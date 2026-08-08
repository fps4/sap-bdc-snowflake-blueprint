"""The simulation's claims, pinned.

These assert the *shape* the simulation is there to demonstrate, not timings —
timings on a laptop are noise, and the report says so too.
"""

from pathlib import Path

from sapbdc.sim.run import run_all


def test_the_three_modes_differ_in_the_ways_the_architecture_claims(tmp_path: Path):
    runs = {r.mode: r for r in run_all(repeats=2, data_dir=tmp_path)}
    rep, fed, shr = runs["REPLICATE"], runs["FEDERATE"], runs["SHARE"]

    # Only replication leaves a second copy in the warehouse.
    assert rep.warehouse_bytes > 10 * fed.warehouse_bytes
    assert rep.warehouse_bytes > 10 * shr.warehouse_bytes

    # Only replication has a job that repeats on every schedule tick.
    assert rep.recurring_seconds > 0
    assert fed.recurring_seconds == 0
    assert shr.recurring_seconds == 0

    # Only federation sees a change posted after setup. A share is a copy someone
    # else operates — its freshness is the producer's promise, not the consumer's
    # schedule — and that is the distinction the register's freshness column makes.
    assert fed.sees_source_change is True
    assert rep.sees_source_change is False
    assert shr.sees_source_change is False

    # The share publishes bytes once; the other two publish nothing.
    assert shr.published_bytes > 0
    assert rep.published_bytes == 0
    assert fed.published_bytes == 0
