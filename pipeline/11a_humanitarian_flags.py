#!/usr/bin/env python3
"""Humanitarian flag per arc row, for the external validation in 11_h2_pca.py.

Re-runs the endpoint resolution of 02_build_graph.py (imported, so the two
cannot diverge) and attaches each row's transaction_sector_code. A row is
sector-coded when its transaction_sector_code list contains at least one
5-digit DAC purpose code (the lists mix vocabularies: a 5-digit purpose code
is usually accompanied by its 3-digit DAC category or a 1-2 digit code of
another vocabulary), and humanitarian when any of its 5-digit codes starts
with 72, 73 or 74 (emergency response, reconstruction relief, disaster
prevention). Rows without a 5-digit code carry hum = NaN. This definition
reproduces the per-organisation shares of the published h2_scores.tsv
exactly on the organisations common to both row sets.

Output: hum_rows.parquet with columns prov, recv, hum (1.0 / 0.0 / NaN),
one row per disbursement row used for arcs. 11_h2_pca.py aggregates it
per organisation (share of sector-coded rows that are humanitarian, over
provider and receiver roles alike).

Usage: python3 11a_humanitarian_flags.py [Data]
"""
import sys
import numpy as np, pandas as pd
import importlib.util
spec = importlib.util.spec_from_file_location("b", "02_build_graph.py"); B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)

HUM = ("72", "73", "74")
t3 = B.load_rows(sys.argv[1] if len(sys.argv) > 1 else "Data")
w = B.resolve_rows(t3)
codes = t3.transaction_sector_code.reindex(w.index).astype("string").str.findall(r"\d+")
def flag(L):
    five = [c for c in L if len(c) == 5] if isinstance(L, list) else []
    return np.nan if not five else float(any(c[:2] in HUM for c in five))
hum = pd.Series(codes.map(flag).astype(float), index=w.index)
out = pd.DataFrame({"prov": w.prov, "recv": w.recv, "hum": hum})
out.to_parquet("hum_rows.parquet", index=False)
print(f"rows: {len(out):,}; sector-coded: {int(hum.notna().sum()):,}; humanitarian: {int((hum == 1).sum()):,}")
