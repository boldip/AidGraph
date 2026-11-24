#!/bin/bash
# Option A: rebuild the whole chain on the v3 graph (generic category codes treated as
# missing references). Logs in logs_A/<step>.log; marker files DONE_A / FAILED_A.
set -eE
cd "$(dirname "$0")"
mkdir -p logs_A; rm -f DONE_A FAILED_A
trap 'echo "FAILED at step $STEP" > FAILED_A' ERR
run() { STEP=$1; shift; echo "[$(date +%H:%M:%S)] $STEP: $*"; "$@" > "logs_A/$STEP.log" 2>&1; }
run 02_build python3 02_build_graph.py Data
for f in nodes.tsv arcs_weighted.tsv; do cmp -s graph/$f ../Revision-SecondSubmission/graph_clean/$f || { echo "graph/$f differs from graph_clean (r9)" > FAILED_A; exit 1; }; done
run 03_distances bash 03_distances.sh
run 04_report python3 04_report.py
run 07_country python3 07_build_country_aid.py
run 12_full python3 12_build_iati_full.py
run 08_h1 python3 08_h1_harmonic.py 960
run 14_outonly python3 14_h1_outonly_null.py 960
run 10_h1report python3 10_h1_report.py
run 11a_hum python3 11a_humanitarian_flags.py Data
run 11_pca python3 11_h2_pca.py
run 09_nulltable python3 09_null_table.py 96
run 19_tables python3 19_h3_tables.py
run 13_funders python3 13_wcc_and_funder_sizes.py
run 18_percolation python3 18_percolation.py
cd ../Revision-SecondSubmission
run r1_ggfree python3 r1_globalgiving_free.py 960
run r2_backbone python3 r2_backbone.py
run r4_figures python3 r4_revision_figures.py
cd ../SecondSubmission
echo "all steps done $(date)" > DONE_A
