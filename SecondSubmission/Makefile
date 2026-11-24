# Reproduction chain for "The Hidden Geometry of Global Aid" (SecondSubmission).
# Inputs : Data (IATI transaction extract, parquet; see SOURCES.md), comparison_data/ (re-downloaded by 06/15 if absent),
#          ~/jars with WebGraph (03_distances.sh; optional, see README).
# Usage  : make all            full chain (null models: ~1.5 h each on 24 cores)
#          make all N=24       smoke test with 24 null samples instead of 960
#          make tables         regenerate every LaTeX table body of the paper
N ?= 960
PY = python3

.PHONY: all graph distances report comparisons h1 h2 h3 percolation tables revision clean

all: graph distances report comparisons h1 h2 h3 percolation tables

graph: graph/arcs_weighted.tsv
graph/arcs_weighted.tsv: 02_build_graph.py Data
	$(PY) 02_build_graph.py Data

distances: graph/nf-exact.txt
graph/nf-exact.txt: graph/arcs_weighted.tsv 03_distances.sh
	bash 03_distances.sh

report: report.md
report.md fig_distance_distribution.png: graph/nf-exact.txt 04_report.py
	$(PY) 04_report.py

comparisons: comparison/airline.tsv comparison/aid_country.tsv comparison/refugee.tsv
comparison/airline.tsv: 06_build_comparisons.py
	$(PY) 06_build_comparisons.py
comparison/aid_country.tsv: 07_build_country_aid.py Data
	$(PY) 07_build_country_aid.py
comparison/refugee.tsv: 15_build_more_comparisons.py
	$(PY) 15_build_more_comparisons.py

funder_scale.tsv graph/arcs_full.tsv: 12_build_iati_full.py Data
	$(PY) 12_build_iati_full.py

h1: h1_top50.tex
h1_ranking.tsv: 08_h1_harmonic.py graph/arcs_weighted.tsv
	$(PY) 08_h1_harmonic.py $(N)
	$(PY) 14_h1_outonly_null.py $(N)
h1_top50.tex fig_h1_z_scatter.png: h1_ranking.tsv funder_scale.tsv ref_names.tsv 10_h1_report.py
	$(PY) 10_h1_report.py

h2: h2_loadings.tex
hum_rows.parquet: 11a_humanitarian_flags.py 02_build_graph.py Data
	$(PY) 11a_humanitarian_flags.py Data
h2_loadings.tex h2_scores.tsv fig_h2_pca.png: hum_rows.parquet 11_h2_pca.py graph/arcs_weighted.tsv
	$(PY) 11_h2_pca.py

h3: null_table.tsv
null_table.tsv: 09_null_table.py comparisons graph/arcs_weighted.tsv
	$(PY) 09_null_table.py $(shell test $(N) -lt 96 && echo $(N) || echo 96)

percolation: percolation.tsv
percolation.tsv fig_percolation.png: 18_percolation.py h1_ranking.tsv funder_scale.tsv
	$(PY) 18_percolation.py

tables: tab_networks.tex tab_nullz.tex tab_measurement.tex
tab_networks.tex tab_nullz.tex tab_measurement.tex: 19_h3_tables.py null_table.tsv comparisons
	$(PY) 19_h3_tables.py
	$(PY) 13_wcc_and_funder_sizes.py

revision:
	cd ../Revision-SecondSubmission && $(PY) r1_globalgiving_free.py $(N) && $(PY) r2_backbone.py && $(PY) r3_name_check_sample.py && $(PY) r4_revision_figures.py

clean:
	rm -f tab_*.tex h3_invariants.tsv hum_rows.parquet
