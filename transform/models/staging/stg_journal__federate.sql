-- The journal read in place, in the source system, on every single query. Nothing
-- at rest and no schedule to fail — paid for with a share of the ERP's capacity,
-- again, each time anyone asks.
{{ journal_from('sap_federated', 'FEDERATE') }}
