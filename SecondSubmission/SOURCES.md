# Data provenance

## Publisher names (`comparison_data/publisher_names.json`, committed)

- **Source**: IATI Registry CKAN API,
  https://iatiregistry.org/api/3/action/organization_list?all_fields=true
  (paginated), downloaded 2026-09-02. Maps publisher IATI org refs
  (uppercased) to display names; used only to label funders in the H1
  ranking (h1_ranking.tsv / h1_top50.tex).

All datasets downloaded 2026-09-02 by the pipeline in this directory
(`06_build_comparisons.py` re-downloads raw files into `comparison_data/`,
gitignored, if absent; derived edge lists are committed under `comparison/`).

## Aid graph (`Data`, gitignored — 652 MB)

- **File**: `IATI_All_Transactions.parquet`, received from Xian (Elaine) Gong
  by email 2026-09-02 ("Re: Aid network paper: proposed reframe for the
  resubmission"); originally retrieved from the IATI datastore API
  (https://api.iatistandard.org/datastore).
- **Content**: 10,115,429 IATI transaction records (all fields stringified
  lists). Graph built from transaction type 3 (disbursements) only:
  3,680,429 rows, 2,583,194 after full-row dedup (matches Elaine's counts).
- **Construction**: see `02_build_graph.py` header for the approved decisions
  (provider imputed from reporting org, receiver-less rows dropped, refs
  uppercased, placeholder refs dropped, count + fixed-rate-USD weights).

## Country-level aid network (`comparison/aid_country.tsv`)

- **Source**: derived from the same IATI parquet as the org-level aid graph
  (`07_build_country_aid.py`).
- **Graph** (revised 2026-09-03): donor→recipient country dyads built from
  the FULL row set — the receiving organisation is NOT required, since the
  dyad's target is the recipient country: `transaction_recipient_country_code`,
  falling back to activity-level `recipient_country_code`. Source country =
  ISO-2 prefix of the provider org ref, or the country of a bilateral
  `XM-DAC-<code>` agency (official OECD DAC donor codes; multilateral
  providers, ~26% of rows, have no country and are excluded). AidData rows
  censored (see below). Same-country rows dropped. Weights: transaction
  count and net USD (same FX table). 1,172,142 rows, $468.6B; n=218,
  m=2,010. (The receiver-identified variant is kept as
  `comparison/aid_country_k.tsv` for reference.)

## IATI (full) graph and funder scale (`graph/arcs_full.tsv`, `funder_scale.tsv`)

- **Source**: same parquet, `12_build_iati_full.py`. IATI-k plus one sink
  node `UNID::<provider>` per provider holding its receiver-less
  disbursements (per-provider, not global, so no cross-publisher merges;
  sinks add no paths). Also emits per-funder identified/unidentified gross
  USD and the receiver-transparency index.

## Censored: AidData (secondary reporter)

- Rows published by `US-501C3-522318905` (AidData, 17,715 rows, $430B) are
  dropped from every graph (`SECONDARY_REPORTERS` in `02_build_graph.py`).
  AidData republishes other donors' activities — its activity ids embed
  World Bank project P-numbers, titles are IBRD/IDA loans — with no provider
  refs, so provider imputation would credit AidData (and the US, at country
  level) with World Bank lending, besides duplicating flows reported via
  World Bank channel codes 44001/44002. None of these rows names a receiver,
  so IATI-k is unaffected.

## Airline network (`comparison/airline.tsv`)

- **Source**: OpenFlights route database, `routes.dat`,
  https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat
  (repository jpatokal/openflights). Route data vintage: June 2014 (the
  OpenFlights route snapshot is frozen).
- **Graph**: nodes = airports (IATA/ICAO code as in the file); directed arc
  src→dst if at least one airline operates the route; w = number of operating
  airlines. Rows with missing endpoint codes dropped. n=3,425, m=37,594.

## World trade network (`comparison/trade.tsv`)

- **Source**: Correlates of War, Trade v4.0 (dyadic),
  https://correlatesofwar.org/wp-content/uploads/COW_Trade_4.0.zip,
  file `Dyadic_COW_4.0.csv`.
- **Citation**: Barbieri, Katherine and Omar M. G. Omar Keshk. 2016.
  Correlates of War Project Trade Data Set Codebook, Version 4.0;
  Barbieri, Keshk & Pollins 2009, "Trading Data: Evaluating our Assumptions
  and Coding Rules", CMPS 26(5).
- **Graph**: year 2014 (latest available); directed arc exporter→importer,
  w = import flow in millions of current USD (`flow1`/`flow2`; −9 = missing
  and non-positive flows dropped). n=186, m=22,451.

## Interbank network (`comparison/interbank.tsv`)

- **Source**: BIS Consolidated Banking Statistics, public bulk file
  https://data.bis.org/static/bulk/WS_CBS_PUB_csv_flat.zip (4.75 GB flat CSV).
- **Filter** (exact codes): measure S (amounts outstanding), bank type 4R
  (domestic banks excl. domestic positions), reporting basis U
  (guarantor/ultimate risk), position C (total claims), instruments A,
  maturity A, currency TO1 (all), **counterparty sector B (banks)**, quarter
  **2025-Q4**; counterparty restricted to ISO-2 country codes (aggregates
  dropped), self-loops and non-positive values dropped. Units: USD millions.
- **Rationale**: true bank-level interbank exposures are confidential;
  the country-level BIS network is the standard public proxy, cf.
  Minoiu & Reyes 2013, "A network analysis of global banking: 1978–2010",
  J. Financial Stability 9(2). n=170 (21 reporters), m=1,169.

## Identity canonicalisation (2026-09-04)

- Suffixed project refs (a real org ref plus a project suffix, e.g.
  GB-CHC-229476-WISH2ACTION belonging to IPPF GB-CHC-229476) are collapsed
  onto the base ref whenever the base itself occurs in the data (102 refs;
  `canonical_map` in `02_build_graph.py`). The existence guard protects
  genuine refs with internal dashes (US-EIN-13-2626135).

## The iati-k+1 variant (`graph/arcs_kplus1.tsv`, gitignored; `17_build_type1_variant.py`)

- Type-1 (incoming funds) rows merged into iati-k: receiver = reporting
  org, provider = named payer; arc-set union, payer-reported weights kept
  where both sides report. 4,764 type-1 arcs (731 two-side-confirmed,
  4,033 new); n=19,311, m=23,678, 2,752 funders incl. USAID. Not yet the
  headline graph; decision pending with co-authors.

## Data v2 (2026-09-08)

- Second extract from Elaine: 10,890,453 rows (+775,024), one new column
  transaction_receiver_org_narrative. Ref-less receivers resolved via a
  conservative name dictionary (publisher titles + within-data name-ref
  co-occurrence, 90% dominance / >=3 observations, junk names blacklisted;
  `name_dictionary` in `02_build_graph.py`): 269,090 rows resolved,
  unmatched named rows stay dropped. v1 dedup had merged >1M rows
  differing only in receiver name. All results recomputed on v2.
