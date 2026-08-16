-- The journal as the producing data product published it: read in place, zero-copy,
-- no ingest. Its freshness is the producer's promise rather than your scheduler's,
-- which is the trade this binding makes and the reason a share is not federation.
{{ journal_from('sap_shared', 'SHARE') }}
