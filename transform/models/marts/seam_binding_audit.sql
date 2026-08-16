-- The three bindings, side by side, answering the one question that separates them.
--
-- `make simulate` changes a single source row *after* every mode has been set up —
-- the way an ERP does when a document is posted a second after your load finished.
-- This model asks each binding whether it noticed:
--
--   FEDERATE  sees it. There is nothing in between to be out of date.
--   REPLICATE does not, until its next delta run.
--   SHARE     does not, until the producer republishes.
--
-- That is the freshness argument stated as a table you can select from, and
-- `tests/assert_only_federation_sees_the_late_change.sql` fails if it ever stops
-- being true. The sentinel amount is `SENTINEL_AMOUNT` in `src/sapbdc/sim/modes.py`;
-- `tests/test_dbtgen.py` keeps the two in step.

{% set bindings = [
    ('REPLICATE', 'stg_journal__replicate'),
    ('FEDERATE',  'stg_journal__federate'),
    ('SHARE',     'stg_journal__share'),
] %}

{% for binding, model in bindings %}

select
    '{{ binding }}'                                             as binding,
    count(*)                                                    as rows_visible,
    round(sum(amount_lc), 2)                                    as amount_lc,
    max(changed_at)                                             as max_changed_at,
    count(*) filter (
        where amount_lc = {{ var('sentinel_amount') }}
    ) > 0                                                       as sees_late_change
from {{ ref(model) }}

{% if not loop.last %}union all{% endif %}

{% endfor %}
