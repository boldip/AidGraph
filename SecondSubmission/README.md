# Reproduction guide (SecondSubmission)

Code for "The Hidden Geometry of Global Aid: How Money Moves Through 10 Million
Transactions" (Scientific Reports, revised version). Everything in the paper is
produced by the numbered scripts below, run in order from this directory;
`make all` runs the chain (see Makefile; `make all N=24` for a smoke test of the
stochastic null models). Round-2 robustness analyses live in
`../Revision-SecondSubmission` (scripts r1 to r9b, shared helpers in common.py).

## Inputs

| Input | Where | Notes |
|---|---|---|
| `Data` | IATI transaction extract, Parquet, 10,890,453 rows, 765 MB | Retrieved from the IATI datastore API (api.iatistandard.org/datastore), second extract of 2026-09-08; deposited with the code. See SOURCES.md. |
| `comparison_data/` | raw files of the five comparison networks | Re-downloaded by 06 and 15 if absent (BIS flat file is 4.75 GB; the KNOMAD remittance matrix is fetched from the Internet Archive). Derived edge lists are committed under `comparison/`. |
| `comparison_data/publisher_names.json` | IATI Registry publisher titles (2026-09-02) | committed |
| `ref_names.tsv` | hand-curated display names for Table 2 | committed |
| WebGraph | `~/jars/*.jar`: webgraph, dsiutils, fastutil, sux4j, jsap (jars dated 2015-04-27, i.e. WebGraph 3.5.x), Java 8 or later | only for 03_distances.sh; `../Revision-SecondSubmission/common.py:distance_distribution` computes the same exact distribution in Python |

Python packages: `requirements.txt` (versions used for the paper).

## Run order and what each step produces

| Step | Script | Produces | Used in the paper for | Time |
|---|---|---|---|---|
| 1 | `01_inspect.py Data` | printed profile | Methods counts | 3 min |
| 2 | `02_build_graph.py Data` | `graph/{arclist.txt,arcs_weighted.tsv,nodes.tsv,build_log.txt}` | IATI-K; Table 1, Extended Data Table 1 | 6 min, 50 GB RAM |
| 3 | `03_distances.sh` | `graph/nf-exact.txt`, `nf-sym.txt`, SCC files | Fig. 1, distance numbers | 2 min |
| 4 | `04_report.py` | `report.md`, `fig_distance_distribution.png`, `fig_degree_distributions.png` | Fig. 1, invariants in text | 1 min |
| 5 | `06_build_comparisons.py`, `07_build_country_aid.py`, `15_build_more_comparisons.py` | `comparison/*.tsv` | the H3 networks | downloads |
| 6 | `12_build_iati_full.py` | `graph/arcs_full.tsv`, `funder_scale.tsv` | IATI-ALL, gross scale, 49.6% / 44% shares | 6 min |
| 7 | `08_h1_harmonic.py 960`, `14_h1_outonly_null.py 960` | `h1_ranking.tsv` | H1 null-model scores | 1.5 h each, 24 cores |
| 8 | `10_h1_report.py` | `h1_top50.tex`, `fig_h1_z_scatter.png` | Table 2, Fig. 3 | seconds |
| 9 | `11a_humanitarian_flags.py Data`, `11_h2_pca.py` | `hum_rows.parquet`, `h2_scores.tsv`, `h2_loadings.tex`, `fig_h2_pca.png` | Fig. 4, Table 3, humanitarian validation | 6 min + seconds |
| 10 | `09_null_table.py 96` | `null_table.tsv` | Extended Data Table (null z) | 1 h |
| 11 | `16_cycle_invariants.py`, `19_h3_tables.py` | `tab_networks.tex`, `tab_nullz.tex`, `tab_measurement.tex`, `h3_invariants.tsv` | H3 tables (main text and Extended Data) | minutes |
| 12 | `13_wcc_and_funder_sizes.py` | `fig_funder_strength.png`, printed stats | funder-size paragraph | seconds |
| 13 | `18_percolation.py` | `percolation.tsv`, `fig_percolation.png` | Fig. 2 (the paper shows the left panel) | 10 min |

Steps 7 and 10 are stochastic (seeded, 24 independent chains); rerunning
reproduces the published z-scores to the second decimal.

## Known manual steps

* The LaTeX table bodies `h1_top50.tex`, `h2_loadings.tex` and the three
  `tab_*.tex` files are included by the manuscript after cosmetic editing of
  headers and column order in Overleaf; the numbers are those of the files.
* The paper's `fig_percolation_v2.png` is the left panel of
  `fig_percolation.png` cropped to PDF.
* Rounding: the scripts round half to even on binary floats; the manuscript
  rounded a few boundary cases half up (e.g. 0.245 shown as 0.25).
