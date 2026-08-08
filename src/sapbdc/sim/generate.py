"""Synthetic SAP-shaped source data, in DuckDB.

Shaped like the tables the catalog names — a universal-journal fact with a
company code, fiscal year/period, account and amount, and the master data it
joins to. Deliberately generated from ``range()`` and ``hash()`` rather than a
random number generator: the same data every run, on every machine, so a timing
difference between two modes is a difference between the modes.

This is a *laptop-scale analogue*, not a benchmark of SAP or Snowflake. What it
demonstrates is the shape — that a federated query re-reads the source every
time, that a replicated one is answered from a second copy you now store, and
that a shared one is answered without either — not how fast any of them is.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

ROWS_JOURNAL = 1_200_000
ROWS_MATERIAL = 20_000
ROWS_CUSTOMER = 5_000
#: Rows carrying a timestamp after the watermark, i.e. the delta a replication
#: flow would pick up on its next run.
DELTA_FRACTION = 0.02

WATERMARK = "2026-06-30 00:00:00"

#: The row each mode's setup is followed by changing, to see which modes notice.
#: Deliberately not a multiple of the delta stride, so it sits in the initial load
#: rather than the delta — the copy has the row, just not the new value.
SENTINEL_ROW_ID = 12_345


def build_source(path: Path) -> Path:
    """(Re)create the source database. Idempotent — deletes and rebuilds."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    con = duckdb.connect(str(path))
    try:
        con.execute(
            f"""
            CREATE TABLE acdoca AS
            SELECT
                i                                              AS row_id,
                lpad(((i % 30) + 1)::VARCHAR, 4, '0')          AS rbukrs,      -- company code
                2025 + ((i / 200000)::INTEGER % 2)             AS gjahr,       -- fiscal year
                ((i % 12) + 1)                                 AS poper,       -- period
                (400000 + (hash(i) % 900))::VARCHAR            AS racct,       -- G/L account
                'EUR'                                          AS rhcur,
                round(((hash(i * 7) % 4000000) / 100.0) - 15000.0, 2) AS hsl,  -- amount
                lpad((hash(i * 3) % {ROWS_MATERIAL})::VARCHAR, 8, '0') AS matnr,
                lpad((hash(i * 11) % {ROWS_CUSTOMER})::VARCHAR, 8, '0') AS kunnr,
                lpad(i::VARCHAR, 10, '0')                      AS belnr,
                TIMESTAMP '2026-01-01 00:00:00'
                    + INTERVAL (i % 180) DAY
                    + INTERVAL ((i * 13) % 86400) SECOND       AS changed_at
            FROM range(0, {ROWS_JOURNAL}) t(i);
            """
        )
        # The delta: a slice of rows re-stamped after the watermark, as an ERP would
        # on a document change. Chosen by modulus, so it is the same slice every run.
        stride = int(1 / DELTA_FRACTION)
        con.execute(
            f"""
            UPDATE acdoca
               SET changed_at = TIMESTAMP '{WATERMARK}' + INTERVAL (row_id % 3600) SECOND,
                   hsl = round(hsl * 1.05, 2)
             WHERE row_id % {stride} = 0;
            """
        )
        con.execute(
            f"""
            CREATE TABLE mara AS
            SELECT
                lpad(i::VARCHAR, 8, '0')                     AS matnr,
                'MTART' || ((hash(i) % 7) + 1)::VARCHAR      AS mtart,   -- material type
                'PLANT' || ((hash(i * 5) % 12) + 1)::VARCHAR AS werks,
                round((hash(i * 17) % 90000) / 100.0, 2)     AS std_cost
            FROM range(0, {ROWS_MATERIAL}) t(i);
            """
        )
        con.execute(
            f"""
            CREATE TABLE kna1 AS
            SELECT
                lpad(i::VARCHAR, 8, '0')                     AS kunnr,
                'Customer ' || i::VARCHAR                    AS name1,
                CASE (hash(i) % 5) WHEN 0 THEN 'DE' WHEN 1 THEN 'NL'
                                   WHEN 2 THEN 'FR' WHEN 3 THEN 'AT' ELSE 'CH' END AS land1
            FROM range(0, {ROWS_CUSTOMER}) t(i);
            """
        )
    finally:
        con.close()
    return path


#: The consumer's question, asked identically in all three modes so the only
#: difference is where the data is and who pays to read it.
BENCHMARK_SQL = """
SELECT a.rbukrs,
       a.gjahr,
       m.mtart,
       count(*)            AS lines,
       round(sum(a.hsl),2) AS amount
  FROM {journal} a
  JOIN {material} m ON m.matnr = a.matnr
 WHERE a.gjahr = 2025
   AND a.poper BETWEEN 1 AND 6
 GROUP BY 1, 2, 3
 ORDER BY amount DESC
 LIMIT 25;
"""
