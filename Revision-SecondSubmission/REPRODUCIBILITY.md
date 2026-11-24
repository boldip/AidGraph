# What reproduces what (assessment of 2026-11-18, updated 2026-11-19 after the v3 rebuild, for the Zenodo deposit)

Since 2026-11-19 every number, figure and table in the paper comes from the clean (v3) graph: generic CRS channel category codes and placeholders are treated as missing receiver references in `02_build_graph.py` (except 44000 and XM-DAC-43000). The whole chain was rerun with `SecondSubmission/run_A.sh` (resumable copies `run_A_resume*.sh`, `Revision-SecondSubmission/run_A_rest.sh`; logs in `SecondSubmission/logs_A/`). The submitted (v2) graph is kept in `Revision-SecondSubmission/graph_v2/` for old/new comparisons.

Paper element -> producing script (SecondSubmission/ unless noted) -> status.

| Element | Script(s) | Inputs | Status |
|---|---|---|---|
| IATI-K graph (nodes, arcs, Table 1 / ED Table 1 counts) | 02_build_graph.py | Data (parquet, 765 MB, gitignored, local copy present; v2 extract received from Elaine 2026-09-08, extraction from the IATI datastore not scripted) | reproducible; parquet must be deposited |
| Fig. 1 distance distribution, ED fit table (degree/strength rows) | 03_distances.sh (WebGraph, Java) + 04_report.py (powerlaw 2.0.0 required) | graph/arclist.txt; jars in ~/jars (public: webgraph, dsiutils, fastutil, sux4j, jsap) | reproducible; jars/versions not in repo; Revision-SecondSubmission/common.py recomputes the same distribution in pure Python |
| Table 2 (H1 ranking), Fig. 3 | 08_h1_harmonic.py, 14_h1_outonly_null.py, 10_h1_report.py, 12_build_iati_full.py (funder_scale.tsv) | graph/, ref_names.tsv (hand-curated display names, committed) | reproducible (null model stochastic: 960 samples, seeded chains) |
| Fig. 2 percolation | 18_percolation.py, then Revision-SecondSubmission/r11_fig2_left.py (left panel alone as PNG) | graph/, funder_scale.tsv, percolation.tsv | reproducible; the submitted fig_percolation_v2.png was a PDF crop of the left panel made by Paul, r11 redraws it |
| Fig. 4, loadings table (PCA) | 11a_humanitarian_flags.py (per-row DAC 72/73/74 flags), 11_h2_pca.py | graph/, Data | reproducible |
| H3 comparison tables (tab:networks, tab:datasets, tab:nullz, cycle table) | 06_build_comparisons.py, 07_build_country_aid.py, 15_build_more_comparisons.py (edge lists, committed under comparison/); 05_compare.py, 09_null_table.py, 16_cycle_invariants.py | comparison_data/ raw files (gitignored, re-downloadable; remit_2021.xlsx only via Internet Archive, BIS flat file 4.75 GB) | reproducible; 19_h3_tables.py writes tab_networks.tex, tab_nullz.tex, tab_measurement.tex (the paper's rows were pasted from them) |
| Funder-size distribution, WCC paragraph, ED fit table (WCC row) and its caption | 13_wcc_and_funder_sizes.py | funder_scale.tsv, graph/ | reproducible |
| 49.6% / 44% identified shares | 12_build_iati_full.py output + build_log | Data | reproducible (printed) |
| h1_top50.tex, h2_loadings.tex in the paper | 10_h1_report.py, 11_h2_pca.py, then Revision-SecondSubmission/r12_paper_tables.py (Paul's layout, display names, reference rows) | h1_ranking.tsv, funder_scale.tsv, h2_loadings.tex | reproducible |
| Round-2 robustness (GG-free, backbones, name audit, clean rebuild) | Revision-SecondSubmission/r1..r9b, common.py | SecondSubmission outputs + Data | reproducible |
| Manuscript markup for the v3 numbers | Revision-SecondSubmission/r10_patch_clean.py (phase 1), r10b_patch_phase2.py (phase 2: tables, captions), r10c_patch_robustness.py (phase 3: GlobalGiving-free, backbone and undirected numbers from r1/r2/r4) | paper/main.tex | applied once each, 2026-11-19; pre-patch source kept as paper/main_before_v3.tex.bak |
| Public code repository https://github.com/boldip/AidGraph | Revision-SecondSubmission/export_code_repo.sh (file list of the two code folders, no paper/, reviews, logs or patch scripts; adds a top-level README and Elaine's extraction README) | working tree | single-commit export, pushed by Paolo |
| Co-author status site | Revision-SecondSubmission/site/build_site.py, deploy_site.sh | notes, paper/, figures | temporary, https://boldi.di.unimi.it/aidnet-rev2-82768dd1c3/ |

Not available anywhere: the first-submission code (superseded), the datastore extraction script (Elaine), the exact WebGraph version used (2015 build, no pom; cited as "WebGraph on Java 27").

Environment notes (2026-11-19): Python 3.15, pandas 3.0.6 (copy-on-write: `to_numpy()` returns read-only views, hence `copy=True` in 09_null_table.py), NumPy 2.5.4, SciPy 1.18.0, matplotlib 3.11.1, powerlaw 2.0.0 (`pip install --user powerlaw`; required by 04, 05, 13). Chain runtime about 5 h, dominated by the 960-sample null models (08, 14, r1) and the null table (09).
