-- The consumer's question, in the semantic layer: journal lines by company code,
-- fiscal period and material type.
--
-- Note what is *not* in this file. There is no mode here, no source name, no hint
-- of whether the journal arrived as a copy, a federated read or a zero-copy share.
-- It refs the decided staging model and stops caring. If flipping ACDOCA from SHARE
-- to REPLICATE required editing this file, the layering would be wrong and the
-- architecture's central claim — that the seam is a property of the seam — would be
-- false in its own repo.

with journal as (

    select * from {{ ref('stg_journal__decided') }}

),

material as (

    select * from {{ ref('stg_material') }}

)

select
    j.company_code,
    j.fiscal_year,
    j.fiscal_period,
    m.material_type,
    count(*)                    as journal_lines,
    round(sum(j.amount_lc), 2)  as amount_lc,
    max(j.changed_at)           as last_changed_at
from journal j
join material m
    on m.material = j.material
group by 1, 2, 3, 4
