#!/usr/bin/env python3
"""Write the H3 comparison tables of the paper as LaTeX table bodies, from
the same code that computed them (05_compare.analyze, 16_cycle_invariants
.invariants, null_table.tsv from 09_null_table.py), so that no number has to
be transcribed by hand.

Outputs (table bodies to \\input):
  tab_networks.tex     main-text Table (tab:networks): 10 columns
  tab_nullz.tex        Extended Data (tab:nullz): value and z for 3 invariants
  tab_measurement.tex  Extended Data (tab:network_measurement): all invariants,
                       cycle columns and the rank-distance Delta to iati-cty
  h3_invariants.tsv    every number, machine-readable
Usage: python3 19_h3_tables.py   (after 02, 06, 07, 15, 09)
"""
import importlib.util, json
import numpy as np, pandas as pd
def load(name):
    spec = importlib.util.spec_from_file_location(name, f"{name}.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
C05 = load("05_compare"); C16 = load("16_cycle_invariants")
C05.plfit = lambda deg: None  # Clauset fits (python-powerlaw) are not part of these tables
NET = [("iati-k", "graph/arcs_weighted.tsv", "count", "Aid, organisations (IATI-K)"),
       ("iati-cty", "comparison/aid_country.tsv", "w", "Aid, countries (IATI-CTY)"),
       ("ibank", "comparison/interbank.tsv", "w", "International banking"),
       ("refugee", "comparison/refugee.tsv", "w", "Refugee movements"),
       ("remit", "comparison/remit.tsv", "w", "Remittances"),
       ("air", "comparison/airline.tsv", "w", "Air routes"),
       ("trade", "comparison/trade.tsv", "w", "Trade")]
rows = []
for key, path, wcol, label in NET:
    arcs = pd.read_csv(path, sep="\t").rename(columns={wcol: "w"})[["s", "d", "w"]]
    r = C05.analyze(arcs, key); r.pop("distance_distribution"); r.pop("plfit_in"); r.pop("plfit_out")
    scc, aoc, tri, c3, f0 = C16.invariants(path)
    r.update(scc_share=scc, cyc_arcs=aoc, c3=c3, f0=f0, label=label); rows.append(r)
    print(key, "done", flush=True)
T = pd.DataFrame(rows).set_index("name")
nz = pd.read_csv("null_table.tsv", sep="\t").set_index("network")
# Delta: rank distance to iati-cty over nine columns (average ranks on ties), as in the report
cols = ["density", "avg_deg", "assortativity", "avg_dist", "eff_diam", "scc_share", "cyc_arcs", "c3", "f0"]
R = T[cols].rank(method="average")
T["delta"] = (R - R.loc["iati-cty"]).abs().sum(axis=1)
T.to_csv("h3_invariants.tsv", sep="\t", float_format="%.6g")

def sgn(x, nd=2): return ("$-$" if x < 0 else "") + f"{abs(x):.{nd}f}"
def sci(d): e = int(np.floor(np.log10(d))); return f"${d/10**e:.1f}\\times10^{{{e}}}$"
def dens(d): return f"${d/10**int(np.floor(np.log10(d))):.1f}\\times10^{{{int(np.floor(np.log10(d)))}}}$" if d < 1e-3 else (f"{d:.4f}" if d < 0.01 else f"{d:.3f}")
def pct(x, nd=1): return "100" if x >= 0.9995 else (f"{100*x:.2f}" if 100*x < 0.1 else f"{100*x:.{nd}f}")
def num(n): return f"{n:,}"
order = ["iati-k", "iati-cty", "ibank", "refugee", "remit", "air", "trade"]
with open("tab_networks.tex", "w") as f:
    for k in order:
        r = T.loc[k]
        f.write(f"{r.label} & {num(int(r.n))} & {num(int(r.m))} & {dens(r.density)} & {pct(r.reciprocity)} & {pct(r.reciprocity_w)} & {sgn(r.assortativity)} & {sgn(r.assortativity_w)} & {r.avg_dist:.2f} & {pct(r.reachable_frac)} & {pct(r.scc_share)}\\\\\n")
        if k == "iati-cty": f.write("\\midrule\n")
with open("tab_nullz.tex", "w") as f:
    for k in order:
        z = nz.loc[k]
        f.write(f"\\textsc{{{k}}} & {z.reciprocity:.3f} & ${z.reciprocity_z:+.1f}$ & ${z.assortativity:.3f}$ & ${z.assortativity_z:+.1f}$ & {z.avg_dist:.2f} & ${z.avg_dist_z:+.1f}$\\\\\n")
with open("tab_measurement.tex", "w") as f:
    rest = T.drop(["iati-k", "iati-cty"]).sort_values("delta").index.tolist()
    for k in ["iati-k", "iati-cty"] + rest:
        r = T.loc[k]; lab = f"\\textsc{{{k}}}"
        delta = "" if k.startswith("iati") else f"{r.delta:.0f}"
        f.write(f"{lab} & {int(r.n):,} & {int(r.m):,} & {sci(r.density)} & {r.avg_deg:.2f} & {r.reciprocity:.3f} & {r.reciprocity_w:.3f} & ${sgn(r.assortativity).replace('$-$', '-')}$ & ${'+' if r.assortativity_w >= 0 else '-'}{abs(r.assortativity_w):.2f}$ & {r.avg_dist:.2f} & {int(r.eff_diam)} & {pct(r.reachable_frac)}\\% & {pct(r.scc_share)}\\% & {pct(r.cyc_arcs)}\\% & {r.c3:.3f} & {r.f0:.3f} & {delta}\\\\\n")
        if k == "iati-cty": f.write("\\midrule\n")
print(open("tab_networks.tex").read()); print(open("tab_nullz.tex").read()); print(open("tab_measurement.tex").read())
