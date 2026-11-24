#!/usr/bin/env python3
"""Two report additions (2026-09-03):
  (a) weakly connected components of IATI-k;
  (b) the size distribution of ALL aid funders: total gross USD disbursed
      per funder from funder_scale.tsv -- partition-independent (does not
      depend on the UNID sink convention), covers the full IATI funder
      universe, with a Clauset fit and CCDF figure.
Outputs: printed stats + fig_funder_strength.png.
"""
import warnings

import numpy as np
import pandas as pd

# ---------- (a) WCC of IATI-k ----------
arcs = pd.read_csv("graph/arcs_weighted.tsv", sep="\t")
n = int(max(arcs.s.max(), arcs.d.max())) + 1
parent = np.arange(n)


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for s, d in zip(arcs.s.to_numpy(), arcs.d.to_numpy()):
    rs, rd = find(s), find(d)
    if rs != rd:
        parent[rs] = rd

roots = np.array([find(x) for x in range(n)])
sizes = np.sort(np.bincount(roots)[np.bincount(roots) > 0])[::-1]
print(f"WCCs: {len(sizes):,}; largest {sizes[0]:,} ({sizes[0]/n:.1%}); "
      f"2nd {sizes[1]:,}; 3rd {sizes[2]:,}")
print(f"components of size 2: {(sizes == 2).sum():,}; size 3-10: "
      f"{((sizes >= 3) & (sizes <= 10)).sum():,}; size >10: {(sizes > 10).sum():,}")
print(f"nodes outside the giant WCC: {n - sizes[0]:,} ({(n - sizes[0])/n:.1%})")

# ---------- (a2) Clauset fits of component size distributions ----------
import struct
import warnings as _w
import powerlaw as _pl

with open("graph/aid.sccsizes", "rb") as f:
    data = f.read()
scc_sizes = np.array(struct.unpack(f">{len(data)//4}i", data))


def compfit(vals, label):
    with _w.catch_warnings():
        _w.simplefilter("ignore")
        try:
            fit = _pl.Fit(vals, discrete=True, verbose=False)
            alpha, xmin = fit.power_law.alpha, fit.power_law.xmin
            try:
                R, p = fit.distribution_compare("power_law", "lognormal",
                                                normalized_ratio=True)
                lr = f"vs lognormal R={R:.2f}, p={p:.3f}"
            except Exception as e:
                lr = f"LR test failed ({type(e).__name__})"
        except Exception as e:
            print(f"{label}: n={len(vals):,}, max={vals.max():,}, "
                  f"fit failed ({type(e).__name__}: {e})")
            return
    print(f"{label}: n={len(vals):,}, max={vals.max():,}, "
          f"alpha={alpha:.2f}, xmin={xmin:.0f}, {lr}")


print(f"sccsizes entries: {len(scc_sizes):,} (isolated nodes may be excluded "
      f"by WebGraph; singletons in file: {(scc_sizes == 1).sum():,})")
compfit(scc_sizes, "SCC sizes (all)")
compfit(sizes, "WCC sizes (all)")
compfit(sizes[1:], "WCC sizes (excl. giant)")

# ---------- (b) funder size distribution (IATI universe) ----------
fs = pd.read_csv("funder_scale.tsv", sep="\t")
u = fs[fs.usd_total > 0].usd_total.to_numpy()
print(f"\nfunders with positive total disbursements: {len(u):,}")
print(f"total {u.sum()/1e9:,.1f}B; median {np.median(u)/1e6:.2f}M; "
      f"top-10 share {np.sort(u)[-10:].sum()/u.sum():.1%}; "
      f"top-1% share {np.sort(u)[-max(1, len(u)//100):].sum()/u.sum():.1%}")

import powerlaw
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    fit = powerlaw.Fit(u, discrete=False, verbose=False)
    R, p = fit.distribution_compare("power_law", "lognormal",
                                    normalized_ratio=True)
print(f"Clauset fit: alpha={fit.power_law.alpha:.2f}, "
      f"xmin={fit.power_law.xmin/1e6:.1f}M; vs lognormal R={R:.2f}, p={p:.3f}")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
INK, MUTED, BLUE = "#333331", "#6f6e69", "#2a78d6"
fig, ax = plt.subplots(figsize=(7.2, 4.6), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
v = np.sort(u)
ax.loglog(v, 1 - np.arange(len(v)) / len(v), ".", ms=3.5, color=BLUE)
ax.set_xlabel("Total gross USD disbursed (funder size)", color=INK)
ax.set_ylabel("CCDF", color=INK)
ax.set_title("Size distribution of all IATI funders "
             f"(n = {len(u):,}; partition-independent)", color=INK,
             fontsize=10)
ax.grid(True, which="major", color="#e8e7e2", lw=0.8)
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
for s_ in ("left", "bottom"):
    ax.spines[s_].set_color("#d4d2cb")
ax.tick_params(colors=MUTED, which="both")
fig.tight_layout()
fig.savefig("fig_funder_strength.png", dpi=150)
print("wrote fig_funder_strength.png")
