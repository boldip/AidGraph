#!/usr/bin/env python3
"""Fig. 2 of the paper = left panel of pipeline/fig_percolation.png (the submitted
version was a PDF crop of that panel).  Redraw it alone from percolation.tsv.

Usage: python3 r11_fig2_left.py [percolation.tsv] [out.png]
"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

src = sys.argv[1] if len(sys.argv) > 1 else "../pipeline/percolation.tsv"
out = sys.argv[2] if len(sys.argv) > 2 else "paper/Figures/fig_percolation_v2.png"
df = pd.read_csv(src, sep="\t")
nf = int(df.k.max())
COL = {"usd": "#2a78d6", "degree": "#eb6834", "harmonic": "#7a52c7"}
LAB = {"usd": "top-$k$ by gross USD", "degree": "top-$k$ by out-degree",
       "harmonic": "top-$k$ by harmonic centrality"}
fig, ax = plt.subplots(figsize=(5.6, 4.4))
rnd = df[df.strategy == "random"].sort_values("k")
x = rnd.k.replace(0, 0.5)
ax.fill_between(x, np.clip(rnd.giant_wcc_share - 2 * rnd.giant_sd, 0, 1),
                np.clip(rnd.giant_wcc_share + 2 * rnd.giant_sd, 0, 1),
                color="#999999", alpha=0.25, lw=0)
ax.set_ylim(-0.02, 1.02)
ax.plot(x, rnd.giant_wcc_share, color="#666666", lw=1.8, label="random $k$ funders")
for s in ["usd", "degree", "harmonic"]:
    d = df[df.strategy == s].sort_values("k")
    ax.plot(d.k.replace(0, 0.5), d.giant_wcc_share, color=COL[s], lw=1.8,
            marker="o", ms=3.5, label=LAB[s])
ax.set_xscale("log")
ax.set_xticks([1, 3, 10, 30, 100, 300, nf])
ax.set_xticklabels(["1", "3", "10", "30", "100", "300", str(nf)])
ax.set_xlabel(f"funders removed, $k$ (of {nf})")
ax.set_title("Largest weakly connected component\n(share of original nodes)", fontsize=10)
ax.grid(alpha=0.25)
ax.set_ylabel("share")
ax.legend(fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(out, dpi=200)
print("wrote", out)
