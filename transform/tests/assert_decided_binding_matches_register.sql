-- The generated bindings must still agree with the register that generated them.
--
-- Two ways this fails, both worth catching. Someone edits `_sources.yml` by hand
-- and the declared mode stops matching the decision. Or someone changes
-- `config/policy.yaml`, a mode moves, and the dbt layer is never regenerated — so
-- the marts quietly keep reading a binding the architecture no longer chose.
--
-- Also asserts that exactly one binding per object is the decided one. Zero would
-- leave `stg_journal__decided` pointing at nothing the register endorses; more than
-- one would mean the generator cannot say which mode won.

with declared as (

    {{ declared_bindings() }}

),

register as (

    select * from {{ ref('decision_register') }}

),

disagrees_with_register as (

    select
        d.object_id,
        'decided_mode ' || d.decided_mode || ' <> register ' || r.mode as problem
    from declared d
    join register r
        on r.object_id = d.object_id
    where d.decided_mode <> r.mode

),

not_exactly_one_decided_binding as (

    select
        object_id,
        'objects with ' || count(*) filter (where is_decided_binding)
            || ' decided bindings, expected 1' as problem
    from declared
    group by object_id
    having count(*) filter (where is_decided_binding) <> 1

)

select * from disagrees_with_register
union all
select * from not_exactly_one_decided_binding
