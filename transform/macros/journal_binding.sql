{#
  One normalisation, used by all three bindings.

  The SAP column names (`rbukrs`, `gjahr`, `poper`, `racct`, `hsl`) become business
  names exactly once. Writing it three times would let the three bindings drift
  apart, and the whole claim being tested here is that they are the *same data*
  arriving three different ways — so any difference between them has to come from
  the mode, never from the SQL.

  `binding` is stamped onto every row so the audit model can tell them apart
  downstream without re-deriving where each one came from.
#}

{% macro journal_from(source_group, binding) %}

select
    row_id,
    rbukrs                       as company_code,
    gjahr                        as fiscal_year,
    poper                        as fiscal_period,
    racct                        as gl_account,
    rhcur                        as currency,
    hsl                          as amount_lc,
    matnr                        as material,
    kunnr                        as customer,
    belnr                        as document_no,
    changed_at                   as changed_at,
    '{{ binding }}'              as binding
from {{ source(source_group, 'acdoca') }}

{% endmacro %}


{#
  The declared bindings, as a relation.

  Reads the generated `_sources.yml` back out of the dbt graph rather than being
  told what it says. That is deliberate: a test that reads the same file the
  generator wrote can catch a hand-edit, and a test that is handed a list cannot.

  `graph` is not populated at parse time, hence the `execute` guard and the
  empty-set fallback — which must still be valid SQL of the right shape.
#}

{% macro declared_bindings() %}

{%- set rows = [] -%}
{%- if execute -%}
    {%- for node in graph.sources.values() -%}
        {%- if node.meta.get('object_id') -%}
            {%- do rows.append(node.meta) -%}
        {%- endif -%}
    {%- endfor -%}
{%- endif -%}

{%- if rows | length == 0 -%}
select
    cast(null as varchar) as object_id,
    cast(null as varchar) as mode,
    cast(null as varchar) as decided_mode,
    cast(null as boolean) as is_decided_binding
where 1 = 0
{%- else -%}
{% for m in rows | sort(attribute='object_id') %}
select
    '{{ m["object_id"] }}'          as object_id,
    '{{ m["mode"] }}'               as mode,
    '{{ m["decided_mode"] }}'       as decided_mode,
    {{ m["is_decided_binding"] }}   as is_decided_binding
{% if not loop.last %}union all{% endif %}
{% endfor %}
{%- endif -%}

{% endmacro %}
