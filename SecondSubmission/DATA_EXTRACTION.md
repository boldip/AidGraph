<!-- Received from Elaine (Xian Gong) on 24 Nov 2026; describes how SecondSubmission/Data (IATI_All_Transactions.parquet, 10,890,453 rows, 25 fields) was extracted from the IATI Datastore. -->

# IATI transaction extract

`IATI_All_Transactions_v2.parquet` contains 10,890,453 transaction records and 25 fields from the International Aid Transparency Initiative (IATI) Datastore. The extraction notebook specifies a transaction value-date window of 1 January 1967 through 31 December 2025, inclusive. 

## Query and filters

We queried the [IATI Datastore transaction endpoint](https://api.iatistandard.org/datastore/transaction/select) by HTTP GET, using a separate query for each calendar year. In the query below, `{year}` denotes the four-digit year.

```text
q=transaction_value_value_date:[{year}-01-01T00:00:00Z TO {year}-12-31T23:59:59Z]
wt=json
rows=1000
start=0
fl=FIELDS
```

The sole inclusion criterion was the transaction value date (`transaction_value_value_date`), in UTC. All transaction types, reporting organisations, recipient countries and sectors were eligible. The `fl` parameter selected the following 25 fields, passed as a comma-separated list.

```text
iati_identifier
reporting_org_ref
transaction_transaction_type_code
transaction_value
transaction_value_currency
transaction_value_value_date
transaction_recipient_country_code
transaction_sector_code
transaction_provider_org_ref
transaction_receiver_org_ref
transaction_receiver_org_narrative
transaction_aid_type_code
transaction_finance_type_code
transaction_flow_type_code
transaction_description_narrative
transaction_provider_org_type
participating_org_narrative
transaction_transaction_date_iso_date
default_currency
title_narrative
budget_value_currency
reporting_org_type
recipient_country_code
participating_org_ref
participating_org_type
```

## From API results to Parquet

We requested up to 1,000 records per page, increasing `start` by the number of records returned until the API returned an empty page. We wrote the results to annual UTF-8 CSV files. The notebook records 58 input files, which we concatenated using pandas. We converted `reporting_org_type` to a string and wrote the combined table to Parquet with `index=False`.

The notebook subsequently created a separate analysis subset by requiring a non-missing receiver organisation narrative, removing duplicate rows and retaining disbursements (transaction type code 3). These steps occurred after the Parquet export.
