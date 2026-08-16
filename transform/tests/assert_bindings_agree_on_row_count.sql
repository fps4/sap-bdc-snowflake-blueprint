-- The three bindings are the same data arriving three different ways.
--
-- If they disagree on how many rows exist, then a difference the architecture
-- attributes to the *mode* is really a difference in the data, and every comparison
-- built on top of them — the audit model, the cost argument, the staleness result —
-- is comparing two things that were never the same to begin with.
--
-- Amounts are deliberately not compared here: they are allowed to differ by exactly
-- the late change, which is the next test's job.

with counts as (

    select binding, rows_visible from {{ ref('seam_binding_audit') }}

)

select
    binding,
    rows_visible,
    (select min(rows_visible) from counts) as min_rows,
    (select max(rows_visible) from counts) as max_rows
from counts
where (select count(distinct rows_visible) from counts) > 1
