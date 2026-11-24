#!/usr/bin/env python3
"""H1 presentation layer: filtered top-50 ranking + scatter figure + TeX table.

Reads h1_ranking.tsv (from 08_h1_harmonic.py). The ranking is restricted to
funders with out-degree >= MIN_DEG and gross USD >= MIN_USD: single-arc
publishers pointing into the core inherit the entire downstream reachable set
(the gateway artifact: 11 degree-1, zero-dollar funders share the maximal
h = 1235.6 via one arc into GB-GOV-10) and are not meaningful aid actors.
Full unfiltered ranking stays in h1_ranking.tsv.

Writes fig_h1_scatter.png and h1_top50.tex (table body to \\input).
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MIN_DEG, MIN_USD = 5, 1e6

f = pd.read_csv("h1_ranking.tsv", sep="\t")
# Scale correction (2026-09-03): a funder's financial scale is EVERYTHING it
# disburses, identified receivers or not. funder_scale.tsv (from
# 12_build_iati_full.py) supplies gross total USD from the full IATI row set;
# without it, funders that name few receivers look small and spuriously
# "punch above their weight".
fs = pd.read_csv("funder_scale.tsv", sep="\t")
f = f.merge(fs[["ref", "usd_total", "transparency"]], on="ref", how="left")
f["usd"] = f.usd_total.fillna(f.usd)

# Display names: registry publisher titles (already in `name`), then the
# most frequent receiver narrative per ref (ref_names.tsv), then pattern
# labels for well-known ref families, then the raw ref.
import re as _re
try:
    rn = pd.read_csv("ref_names.tsv", sep="\t").set_index("ref")["name"]
    f["name"] = f["name"].fillna(f.ref.map(rn))
except FileNotFoundError:
    pass


def _pattern_label(ref):
    m = _re.match(r"^XM-OCHA-CBPF-([A-Z]{3})\d*$", ref)
    if m:
        return f"OCHA Country-Based Pooled Fund ({m.group(1)})"
    return None


f["name"] = f["name"].fillna(f.ref.map(_pattern_label))
g = f[(f.out_degree >= MIN_DEG) & (f.usd >= MIN_USD)].copy()
g["rank_usd_f"] = g.usd.rank(ascending=False).astype(int)
g["rank_z_f"] = g.z.rank(ascending=False).astype(int)
top = g.nlargest(50, "z")
print(f"{len(g)} funders pass the activity filter "
      f"(out-degree >= {MIN_DEG}, gross USD >= {MIN_USD:g})")
tz, tu = set(g.nlargest(50, "z").ref), set(g.nlargest(50, "usd").ref)
print(f"overlap of filtered top-50 by z with top-50 by USD: {len(tz & tu)}")

def texesc(s):
    return (s.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")
             .replace("#", "\\#").replace("$", "\\$"))

has_z2 = "z_outonly" in top.columns and top.z_outonly.notna().any()
rows = []
for i, (_, r) in enumerate(top.iterrows(), 1):
    label = r["name"] if isinstance(r["name"], str) else r.ref
    z2 = f" & {r.z_outonly:.2f}" if has_z2 else ""
    rows.append(f"{i} & {texesc(label[:44])} & {int(r.out_degree)} & "
                f"{r.usd/1e6:,.1f} & {r.h:,.0f} & {r.z:.2f}{z2} & "
                f"{int(r.rank_usd_f)}\\\\")
# reference rows: the giants and the negative outlier, with their z-rank
g = g.assign(rank_z_all=g.z.rank(ascending=False))
ncols = 8 if has_z2 else 7
refrows = [f"\\midrule\n\\multicolumn{{{ncols}}}{{l}}{{\\emph{{reference "
           f"rows (position in the full ranking of {len(g)})}}}}\\\\"]
for rref in ["US-GOV-1", "GB-GOV-1", "XM-DAC-3-1", "US-EIN-300108263"]:
    rr = g[g.ref == rref]
    if not len(rr):
        continue
    r = rr.iloc[0]
    label = r["name"] if isinstance(r["name"], str) else r.ref
    z2 = f" & {r.z_outonly:.2f}" if has_z2 else ""
    refrows.append(f"({int(r.rank_z_all)}) & {texesc(label[:44])} & "
                   f"{int(r.out_degree)} & {r.usd/1e6:,.1f} & {r.h:,.0f} & "
                   f"{r.z:.2f}{z2} & {int(r.rank_usd_f)}\\\\")

with open("h1_top50.tex", "w") as out:
    cols = "rlrrrrrr" if has_z2 else "rlrrrrr"
    z2h = " & $z_{\\mathrm{out}}$" if has_z2 else ""
    out.write(f"\\begin{{tabular}}{{{cols}}}\n\\toprule\n"
              f"\\# & funder & out-deg & USD (M) & $h$ & $z${z2h} & scale rank\\\\\n"
              "\\midrule\n" + "\n".join(rows) + "\n"
              + "\n".join(refrows) + "\n\\bottomrule\n"
              "\\end{tabular}\n")

# --- figure ---
BLUE, ORANGE, INK, MUTED = "#2a78d6", "#eb6834", "#333331", "#6f6e69"
fit = g[g.usd > 0]
X = np.stack([np.ones(len(fit)), np.log10(fit.usd)], axis=1)
beta, *_ = np.linalg.lstsq(X, fit.h.to_numpy(), rcond=None)
fig, ax = plt.subplots(figsize=(8.4, 5.2), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
ax.scatter(g.usd, g.h, s=16, c=BLUE, alpha=0.6, linewidths=0, zorder=2)
xs = np.logspace(np.log10(g.usd.min()), np.log10(g.usd.max()), 50)
ax.plot(xs, beta[0] + beta[1] * np.log10(xs), color=MUTED, lw=2, zorder=1)
hi = g.nlargest(6, "z")
ax.scatter(hi.usd, hi.h, s=52, c=ORANGE, edgecolors="#fcfcfb",
           linewidths=2, zorder=3)
offsets = [(8, 2), (8, -14), (-4, 10), (8, -2), (-30, -16), (8, 8)]
SHORT = {"The William and Flora Hewlett Foundation": "Hewlett Foundation",
         "United States Department of Commerce": "US Dept of Commerce"}
for (off, (_, r)) in zip(offsets, hi.iterrows()):
    label = r["name"] if isinstance(r["name"], str) else r.ref
    ax.annotate(SHORT.get(label, label)[:32], (r.usd, r.h),
                textcoords="offset points", xytext=off, fontsize=7, color=INK)
# context anchors: structure-poor mega-hub and scale-consistent bilaterals
for ref, lbl, off in [("US-EIN-300108263", "GlobalGiving.org (z = −13)", (8, 0)),
                      ("GB-GOV-1", "FCDO (z = −0.4)", (8, -2)),
                      ("XM-DAC-3-1", "Danida (z = −0.4)", (6, -14))]:
    r = g[g.ref == ref].iloc[0]
    ax.scatter([r.usd], [r.h], s=40, c=MUTED, edgecolors="#fcfcfb",
               linewidths=2, zorder=3)
    ax.annotate(lbl, (r.usd, r.h), textcoords="offset points", xytext=off,
                fontsize=7, color=MUTED)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Gross USD disbursed (scale)", color=INK)
ax.set_ylabel("Outgoing harmonic centrality", color=INK)
ax.set_title("Structural importance vs financial scale — funders passing the "
             "activity filter\n(orange: top 6 by degree-preserving-null z)",
             color=INK, fontsize=10)
ax.grid(True, which="major", color="#e8e7e2", lw=0.8, zorder=0)
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
for s_ in ("left", "bottom"):
    ax.spines[s_].set_color("#d4d2cb")
ax.tick_params(colors=MUTED, which="both")
fig.tight_layout()
fig.savefig("fig_h1_scatter.png", dpi=150)

# --- companion figure: z vs scale (the adjustment's result; flat by design) ---
from scipy import stats as _st
gz = g.dropna(subset=["z"])
lx = np.log10(gz.usd)
zb1, zb0, zr, zp, _ = _st.linregress(lx, gz.z)
fig, ax = plt.subplots(figsize=(8.4, 5.2), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
ax.axhline(0, color="#d4d2cb", lw=1, zorder=1)
ax.scatter(gz.usd, gz.z, s=16, c=BLUE, alpha=0.6, linewidths=0, zorder=2)
xs = np.logspace(np.log10(gz.usd.min()), np.log10(gz.usd.max()), 50)
ax.plot(xs, zb0 + zb1 * np.log10(xs), color=MUTED, lw=2, zorder=1)
hi = gz.nlargest(6, "z")
ax.scatter(hi.usd, hi.z, s=52, c=ORANGE, edgecolors="#fcfcfb",
           linewidths=2, zorder=3)
for off, (_, r) in zip(offsets, hi.iterrows()):
    label = r["name"] if isinstance(r["name"], str) else r.ref
    ax.annotate(SHORT.get(label, label)[:30], (r.usd, r.z),
                textcoords="offset points", xytext=off, fontsize=7, color=INK)
for ref, lbl, off in [("US-EIN-300108263", "GlobalGiving.org", (8, 0)),
                      ("GB-GOV-1", "FCDO", (8, -3)),
                      ("XM-DAC-3-1", "Danida", (6, -12))]:
    r = gz[gz.ref == ref].iloc[0]
    ax.scatter([r.usd], [r.z], s=40, c=MUTED, edgecolors="#fcfcfb",
               linewidths=2, zorder=3)
    ax.annotate(lbl, (r.usd, r.z), textcoords="offset points", xytext=off,
                fontsize=7, color=MUTED)
ax.set_xscale("log")
ax.set_xlabel("Gross USD disbursed (scale, identified + unidentified)",
              color=INK)
ax.set_ylabel("z (degree-preserving null)", color=INK)
ax.set_title(f"Null-model z vs financial scale (OLS slope {zb1:+.3f}, "
             f"p = {zp:.2f}, R² = {zr**2:.3f})", color=INK, fontsize=10)
ax.grid(True, which="major", color="#e8e7e2", lw=0.8, zorder=0)
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
for s_ in ("left", "bottom"):
    ax.spines[s_].set_color("#d4d2cb")
ax.tick_params(colors=MUTED, which="both")
fig.tight_layout()
fig.savefig("fig_h1_z_scatter.png", dpi=150)
print("wrote h1_top50.tex, fig_h1_scatter.png, fig_h1_z_scatter.png")
