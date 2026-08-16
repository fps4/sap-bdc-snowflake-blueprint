-- R1, enforced where the violation would actually happen.
--
-- The decision engine holds objects in SAP on residency and personal-data grounds.
-- A register that says so is a document; this is the version that stops a build.
-- Any source declared in this project whose object the engine held back is a
-- residency breach waiting for someone to write a `select`.
--
-- Reads the sources out of the dbt graph rather than trusting a list, so a
-- hand-edited `_sources.yml` is caught too — see `macros/journal_binding.sql`.

with declared as (

    {{ declared_bindings() }}

),

register as (

    select * from {{ ref('decision_register') }}

)

select
    r.object_id,
    r.mode,
    r.rule_id,
    d.mode as declared_binding
from register r
join declared d
    on d.object_id = r.object_id
where r.mode = 'KEEP_IN_SAP'
