# AidGraph: code for "The Hidden Geometry of Global Aid"

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24527392.svg)](https://doi.org/10.5281/zenodo.24527392)

Analysis code and derived files for *The Hidden Geometry of Global Aid: How Money Moves
Through 10 Million Transactions* (McCarthy, Gong, Rizoiu, Boldi; Scientific Reports,
under revision). Everything in the paper (network construction, distances, null models,
funder-removal experiment, PCA, cross-network comparison, robustness analyses) is produced
by the scripts in this repository from the IATI transaction extract described below.

## Layout

* `pipeline/`: the main chain, numbered in run order (`02_build_graph.py` ...
  `19_h3_tables.py`), with `README.md` (run order, inputs, runtimes), `Makefile`
  (`make all`; `make all N=24` for a smoke test), `requirements.txt`, the hand-curated
  `ref_names.tsv`, the comparison edge lists under `comparison/`, and the derived outputs
  (rankings, invariants, figures, table bodies). `DATA_EXTRACTION.md` documents the IATI
  Datastore query that produced the transaction extract.
* `revision/`: the analyses added in the second round of revision
  (`r1` GlobalGiving-free rerun, `r2` backbones, `r3`-`r8` name audit, `r9` clean rebuild,
  `r4`, `r11`, `r12` paper figures and tables, `common.py`), their results (`*_results.md`,
  `*.tsv`, `*.png`), the submitted graph (`graph_v2/`) and the rebuilt one (`graph_clean/`),
  and `REPRODUCIBILITY.md`, which maps every element of the paper to the script that
  produces it.

## Data

The IATI extract (`pipeline/Data`, a 765 MB parquet file, 10,890,453 rows) is not
in the repository; it is deposited on Zenodo as a separate record (DOI [10.5281/zenodo.24543614](https://doi.org/10.5281/zenodo.24543614)).
The comparison datasets (BIS, Correlates of War, OpenFlights, UNHCR, KNOMAD) are public;
sources and snapshots are listed in Extended Data Table 1 of the paper and in
`pipeline/README.md`.

## Archived version

The version used for the article is release v1.0.1, archived on Zenodo with DOI
[10.5281/zenodo.24527392](https://doi.org/10.5281/zenodo.24527392) (concept DOI for all
versions: [10.5281/zenodo.24527391](https://doi.org/10.5281/zenodo.24527391)).

## Environment

Python 3.15, pandas 3.0, NumPy 2.5, SciPy 1.18, matplotlib 3.11, powerlaw 2.0; WebGraph
(Java) for the shortest-path distributions of `03_distances.sh`, which `common.py` can also
recompute in pure Python. The full chain takes about five hours, dominated by the
960-sample null models.

## License

Copyright 2026 Paul X. McCarthy, Xian Gong, Marian-Andrei Rizoiu and Paolo Boldi.
Released under the Apache License, Version 2.0 (see `LICENSE`).
