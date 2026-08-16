-- The staleness result from FS-0004, restated as something that can fail.
--
-- One source row is changed after every mode has been set up. Federation sees it
-- because it re-reads the source; the copy does not until its next delta run; the
-- share does not until the producer republishes. That asymmetry is the reason
-- "zero-copy" and "live" are not synonyms, and it is asserted here rather than only
-- described, because a claim nobody re-checks is a claim that quietly stops holding.
--
-- Fails in both directions: a binding that should see the change and does not, and
-- a binding that should not see it and does.

with expected as (

    select 'FEDERATE'  as binding, true  as should_see
    union all select 'REPLICATE', false
    union all select 'SHARE',     false

)

select
    e.binding,
    e.should_see,
    a.sees_late_change,
    case
        when e.should_see then 'federation must see a change posted after setup'
        else 'this binding must not see a change the producer has not republished'
    end as expectation
from expected e
join {{ ref('seam_binding_audit') }} a
    on a.binding = e.binding
where a.sees_late_change <> e.should_see
