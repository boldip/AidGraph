#!/usr/bin/env python3
"""Regenerate the two \\input tables of the paper in the submitted (Paul's) layout:
paper/h1_top50.tex from SecondSubmission/h1_ranking.tsv + funder_scale.tsv (same filter as
10_h1_report.py) and paper/h2_loadings.tex from SecondSubmission/h2_loadings.tex."""
import re
import pandas as pd

SS = "../SecondSubmission/"
from paper_names import NAMES, CBPF, display  # noqa: F401


def num(x, nd=2):
    s = f"{x:,.{nd}f}"
    return f"$-{s[1:]}$" if s.startswith("-") else s


f = pd.read_csv(SS + "h1_ranking.tsv", sep="\t")
fs = pd.read_csv(SS + "funder_scale.tsv", sep="\t")
f = f.merge(fs[["ref", "usd_total"]], on="ref", how="left")
f["usd"] = f.usd_total.fillna(f.usd)
try:
    rn = pd.read_csv(SS + "ref_names.tsv", sep="\t").set_index("ref")["name"]
    f["name"] = f["name"].fillna(f.ref.map(rn))
except FileNotFoundError:
    pass
g = f[(f.out_degree >= 5) & (f.usd >= 1e6)].copy()
N = len(g)
g["rank_usd_f"] = g.usd.rank(ascending=False).astype(int)
g["rank_z_f"] = g.z.rank(ascending=False, method="first").astype(int)
top = g.nlargest(50, "z")


def row(lead, r):
    return (f"{lead} & {display(r['name'], r.ref)} & {int(r.rank_usd_f)} & {r.usd/1e6:,.1f} & "
            f"{int(r.out_degree):,} & {num(r.z_outonly)} & {r.h:,.0f} & {num(r.z)}\\\\")


lines = ["\\begin{tabular}{rlrrrrrr}", "\\toprule",
         " & & \\multicolumn{3}{c}{Size} & \\multicolumn{3}{c}{Centrality}\\\\",
         "\\cmidrule(lr){3-5}\\cmidrule(lr){6-8}",
         "\\# & Funder & Scale rank & Paid out (US\\$m) & Recipients & Looser test ($z_{\\mathrm{out}}$) & Raw ($h$) & Adjusted ($z$)\\\\",
         "\\midrule"]
lines += [row(i, r) for i, (_, r) in enumerate(top.iterrows(), 1)]
lines += ["\\midrule",
          f"\\multicolumn{{8}}{{l}}{{\\emph{{For comparison: the largest bilateral agencies and the lowest-scoring funder (position among all {N})}}}}\\\\"]
for ref in ["US-GOV-1", "GB-GOV-1", "XM-DAC-3-1", "US-EIN-300108263"]:
    r = g[g.ref == ref].iloc[0]
    lines.append(row(f"({int(r.rank_z_f)})", r))
lines += ["\\bottomrule", "\\end{tabular}"]
open("paper/h1_top50.tex", "w").write("\n".join(lines))
print(f"paper/h1_top50.tex: {N} filtered funders")

# ---------------------------------------------------------------- loadings
LAB = {"in-degree": "Number of funders", "out-degree": "Number of recipients",
       "in-transactions": "Payments received", "out-transactions": "Payments made",
       "USD received": "Money received", "USD disbursed": "Money paid out",
       "mean incoming txn size": "Average payment received", "mean outgoing txn size": "Average payment made",
       "funder ratio": "Share of payments outgoing", "HHI (in)": "Concentration of funders",
       "HHI (out)": "Concentration of recipients", "explained variance": "Share of variation explained"}
out = ["\\begin{tabular}{lrrrr}", "\\toprule",
       " & Giving vs. & Money & Few or many & Few or many\\\\",
       " & receiving & coming in & funders & recipients\\\\",
       "Measure & (PC1) & (PC2) & (PC3) & (PC4)\\\\", "\\midrule"]
for line in open(SS + "h2_loadings.tex"):
    line = line.strip()
    if not line.endswith("\\\\") or line.startswith("feature"):
        if line == "\\midrule" and len(out) > 6:
            out.append(line)
        continue
    cells = [c.strip() for c in line[:-2].split("&")]
    lab = LAB[cells[0]]
    vals = []
    for c in cells[1:]:
        if c.endswith("%"):
            vals.append(c if c.endswith("\\%") else c.replace("%", "\\%"))
            continue
        v = float(c)
        t = num(v)
        vals.append(f"\\textbf{{{t}}}" if abs(v) >= 0.35 else t)
    out.append(f"{lab} & " + " & ".join(vals) + "\\\\")
out += ["\\bottomrule", "\\end{tabular}"]
open("paper/h2_loadings.tex", "w").write("\n".join(out))
print("paper/h2_loadings.tex written")
