-- Material master, arriving over the same share. Master data is the easiest case for
-- zero-copy: small, slow-moving, and joined by everyone — so the copy nobody needed
-- is the copy everyone would otherwise have made.
select
    matnr     as material,
    mtart     as material_type,
    werks     as plant,
    std_cost  as standard_cost
from {{ source('sap_shared', 'mara') }}
