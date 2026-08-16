-- The journal as a second copy you own: landed by an initial load, kept current by
-- a delta job that runs on every schedule tick. Cheap to query, and the only one of
-- the three that costs storage and an on-call rota.
{{ journal_from('sap_replicated', 'REPLICATE') }}
