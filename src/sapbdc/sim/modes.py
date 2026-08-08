"""The three modes, actually executed — so the trade-off is demonstrated, not asserted.

Each function answers the *same* consumer question against the *same* source and
reports what the mode obliges you to own:

* :func:`run_replicate` — a second copy in the warehouse, kept current by a delta
  load against a watermark. The copy is yours to store and the delta run is yours
  to operate, on every schedule tick, forever.
* :func:`run_federate`  — a view over the source. Nothing stored, nothing
  scheduled, and the source is re-read on every question.
* :func:`run_share`     — the producer publishes an object once; the consumer
  reads it in place. No ingest, no second copy, and the producer's refresh
  cadence — not the consumer's — decides how fresh it is.

**What this can and cannot show.** DuckDB plays both sides: an attached read-only
database is the SAP source, the working database is Snowflake, a Parquet file is
the Delta-Sharing object. On one machine with one storage engine, the *query
times* come out nearly identical by construction — the real federation penalty is
a network hop into a system that is also running the business, and no laptop
reproduces that. So the numbers worth reading here are the ones the substitution
does not destroy: bytes at rest, the recurring cost of the delta run, and which
mode sees a source change and which does not. See ADR-0001.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .generate import BENCHMARK_SQL, SENTINEL_ROW_ID, WATERMARK

#: The amount stamped onto one source row after every mode is set up, to see
#: which modes notice.
SENTINEL_AMOUNT = 999999.99


@dataclass(frozen=True)
class ModeRun:
    mode: str
    setup_seconds: float
    recurring_seconds: float
    query_seconds_median: float
    warehouse_bytes: int
    published_bytes: int
    rows_moved: int
    sees_source_change: bool
    owns: str
    detail: str


def _median(values: list[float]) -> float:
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def _time_queries(con: duckdb.DuckDBPyConnection, sql: str, repeats: int) -> list[float]:
    timings = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        con.execute(sql).fetchall()
        timings.append(time.perf_counter() - t0)
    return timings


def _fresh_warehouse(path: Path) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    return duckdb.connect(str(path))


def stamp_source_change(source: Path) -> None:
    """Change one row in the source, the way an ERP would when a document is posted."""
    con = duckdb.connect(str(source))
    try:
        con.execute(
            "UPDATE acdoca SET hsl = ?, changed_at = TIMESTAMP '2026-07-01 09:00:00' "
            "WHERE row_id = ?;",
            [SENTINEL_AMOUNT, SENTINEL_ROW_ID],
        )
    finally:
        con.close()


_PROBE = "SELECT count(*) FROM {journal} WHERE hsl = ?;"


def _probe(warehouse: Path, journal: str, attach: Path | None) -> bool:
    con = duckdb.connect(str(warehouse))
    try:
        if attach is not None:
            con.execute(f"ATTACH '{attach}' AS src (READ_ONLY);")
        hits = con.execute(_PROBE.format(journal=journal), [SENTINEL_AMOUNT]).fetchone()[0]
    finally:
        con.close()
    return bool(hits)


def run_replicate(source: Path, warehouse: Path, repeats: int = 5) -> ModeRun:
    """Initial load plus a watermark delta, then query the copy."""
    con = _fresh_warehouse(warehouse)
    try:
        con.execute(f"ATTACH '{source}' AS src (READ_ONLY);")
        t0 = time.perf_counter()
        con.execute(
            f"CREATE TABLE acdoca AS SELECT * FROM src.acdoca "
            f"WHERE changed_at <= TIMESTAMP '{WATERMARK}';"
        )
        con.execute("CREATE TABLE mara AS SELECT * FROM src.mara;")
        initial = con.execute("SELECT count(*) FROM acdoca;").fetchone()[0]
        setup = time.perf_counter() - t0

        # The delta run — the part that repeats on every schedule tick. Delete then
        # insert by key, because a changed document is an update, not an append:
        # the detail that turns "we just replicate it nightly" into a real pipeline
        # with a real failure mode.
        t1 = time.perf_counter()
        con.execute(
            f"CREATE TEMP TABLE delta AS SELECT * FROM src.acdoca "
            f"WHERE changed_at > TIMESTAMP '{WATERMARK}';"
        )
        delta_rows = con.execute("SELECT count(*) FROM delta;").fetchone()[0]
        con.execute("DELETE FROM acdoca WHERE row_id IN (SELECT row_id FROM delta);")
        con.execute("INSERT INTO acdoca SELECT * FROM delta;")
        con.execute("DROP TABLE delta;")
        recurring = time.perf_counter() - t1

        con.execute("DETACH src;")
        timings = _time_queries(con, BENCHMARK_SQL.format(journal="acdoca", material="mara"), repeats)
        con.execute("CHECKPOINT;")
    finally:
        con.close()

    warehouse_bytes = warehouse.stat().st_size
    stamp_source_change(source)
    sees = _probe(warehouse, "acdoca", attach=None)

    return ModeRun(
        mode="REPLICATE",
        setup_seconds=setup,
        recurring_seconds=recurring,
        query_seconds_median=_median(timings),
        warehouse_bytes=warehouse_bytes,
        published_bytes=0,
        rows_moved=initial + delta_rows,
        sees_source_change=sees,
        owns="a second copy at rest, and a delta job that runs on every schedule tick",
        detail=(
            f"initial load {initial:,} rows, then a delta upsert of {delta_rows:,} rows "
            f"that repeats forever; the source change posted after the run is invisible "
            f"until the next one"
        ),
    )


def run_federate(source: Path, warehouse: Path, repeats: int = 5) -> ModeRun:
    """A view over the source. Nothing is stored; the source is read every time."""
    con = _fresh_warehouse(warehouse)
    try:
        t0 = time.perf_counter()
        con.execute(f"ATTACH '{source}' AS src (READ_ONLY);")
        con.execute("CREATE VIEW acdoca_remote AS SELECT * FROM src.acdoca;")
        con.execute("CREATE VIEW mara_remote AS SELECT * FROM src.mara;")
        setup = time.perf_counter() - t0
        timings = _time_queries(
            con, BENCHMARK_SQL.format(journal="acdoca_remote", material="mara_remote"), repeats
        )
        con.execute("CHECKPOINT;")
    finally:
        con.close()

    warehouse_bytes = warehouse.stat().st_size
    stamp_source_change(source)
    sees = _probe(warehouse, "acdoca_remote", attach=source)

    return ModeRun(
        mode="FEDERATE",
        setup_seconds=setup,
        recurring_seconds=0.0,
        query_seconds_median=_median(timings),
        warehouse_bytes=warehouse_bytes,
        published_bytes=0,
        rows_moved=0,
        sees_source_change=sees,
        owns="nothing at rest and no schedule — but a share of the source system's load, "
        "paid again on every question",
        detail=(
            "two views and no pipeline; the source change is visible immediately, "
            "because there is nothing in between to be out of date"
        ),
    )


def run_share(source: Path, warehouse: Path, share_dir: Path, repeats: int = 5) -> ModeRun:
    """The producer publishes an object once; the consumer reads it in place."""
    share_dir.mkdir(parents=True, exist_ok=True)
    journal = share_dir / "acdoca.parquet"
    material = share_dir / "mara.parquet"

    t0 = time.perf_counter()
    src = duckdb.connect(str(source), read_only=True)
    try:
        # Published by the producing data product, not by a pipeline the consumer
        # operates. That distinction is the whole economic argument for sharing —
        # and the reason a share's freshness is the producer's promise, not yours.
        src.execute(f"COPY acdoca TO '{journal}' (FORMAT PARQUET, COMPRESSION ZSTD);")
        src.execute(f"COPY mara TO '{material}' (FORMAT PARQUET, COMPRESSION ZSTD);")
        published = src.execute("SELECT count(*) FROM acdoca;").fetchone()[0]
    finally:
        src.close()
    setup = time.perf_counter() - t0

    con = _fresh_warehouse(warehouse)
    try:
        con.execute(f"CREATE VIEW acdoca_shared AS SELECT * FROM read_parquet('{journal}');")
        con.execute(f"CREATE VIEW mara_shared AS SELECT * FROM read_parquet('{material}');")
        timings = _time_queries(
            con, BENCHMARK_SQL.format(journal="acdoca_shared", material="mara_shared"), repeats
        )
        con.execute("CHECKPOINT;")
    finally:
        con.close()

    warehouse_bytes = warehouse.stat().st_size
    published_bytes = journal.stat().st_size + material.stat().st_size
    stamp_source_change(source)
    sees = _probe(warehouse, "acdoca_shared", attach=None)

    return ModeRun(
        mode="SHARE",
        setup_seconds=setup,
        recurring_seconds=0.0,
        query_seconds_median=_median(timings),
        warehouse_bytes=warehouse_bytes,
        published_bytes=published_bytes,
        rows_moved=published,
        sees_source_change=sees,
        owns="nothing at rest and no schedule — but the producer's refresh cadence, "
        "which is a dependency you do not control",
        detail=(
            f"{published:,} rows published once as {published_bytes / 1e6:,.1f} MB of "
            f"columnar objects and read in place; the warehouse stores nothing, and the "
            f"source change waits for the producer to republish — a share is not "
            f"federation"
        ),
    )
