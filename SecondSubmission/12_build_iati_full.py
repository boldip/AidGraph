#!/usr/bin/env python3
"""Build the IATI (full) graph: IATI-k plus per-provider UNIDENTIFIED sinks.

Two-graph design (agreed 2026-09-03):
  IATI-k  = the identified-receiver graph (graph/arcs_weighted.tsv, unchanged)
            -- owns everything path-based (distances, centralities, nulls,
            PCA wiring features), since unidentified receivers are sinks and
            add no paths.
  IATI    = all disbursement rows with an identifiable provider. Rows whose
            receiver is unidentified are routed to one sink node per
            provider ("UNID::<provider>"): a per-provider aggregate with a
            generative meaning (the provider's unreported downstream), no
            cross-provider false merges. Owns actor universe, volumes,
            out-degree/strength distributions, H1's scale variable, and the
            per-funder receiver-transparency index.

Outputs:
  graph/arcs_full.tsv, graph/nodes_full.tsv  - the IATI graph
  funder_scale.tsv - per funder: identified/unidentified gross USD and txns,
                     transparency = identified gross USD / total gross USD
  printed panel: n, m, density, volume, funders for both graphs.

Gross USD = sum of positive disbursement values (row level, fixed FX table).
"""
import importlib.util

import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location("bg", "02_build_graph.py")
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)
unwrap, FX, PLACEHOLDER = bg.unwrap, bg.FX, bg.PLACEHOLDER
SECONDARY_REPORTERS = bg.SECONDARY_REPORTERS


def main():
    cols = ["transaction_transaction_type_code", "transaction_provider_org_ref",
            "transaction_receiver_org_ref", "reporting_org_ref",
            "transaction_value", "transaction_value_currency", "default_currency"]
    t3 = pd.read_parquet("Data")
    t3 = t3[t3.transaction_transaction_type_code == "['3']"].drop_duplicates()
    print(f"deduplicated type-3 rows: {len(t3):,}")
    sec = t3.reporting_org_ref.map(unwrap).str.upper().isin(SECONDARY_REPORTERS)
    t3 = t3[~sec]
    print(f"secondary-reporter rows dropped (AidData): {sec.sum():,}")

    prov = t3.transaction_provider_org_ref.map(unwrap)
    prov = prov.fillna(t3.reporting_org_ref.map(unwrap)).str.upper()
    prov = prov.where(~bg.is_placeholder(prov))
    recv = t3.transaction_receiver_org_ref.map(unwrap).str.upper()
    recv = recv.where(~bg.is_placeholder(recv))  # v3: generic category codes are missing refs too
    usd = (t3.transaction_value.map(unwrap).astype(float)
           * t3.transaction_value_currency.map(unwrap)
             .fillna(t3.default_currency.map(unwrap)).map(FX))

    # same receiver-name dictionary resolution as 02 (v2, 2026-09-08)
    if "transaction_receiver_org_narrative" in t3.columns:
        rname = t3.transaction_receiver_org_narrative.map(unwrap).map(bg.norm_name)
        rname = rname.where(rname.notna()
                            & ~rname.str.contains(bg.JUNK_NAME, na=False))
        d = bg.name_dictionary(recv, rname)
        fill = recv.isna() & rname.notna()
        recv = recv.where(recv.notna(), rname[fill].map(d))
        print(f"receivers resolved by name dictionary: {fill.sum():,} candidates")
    cmap = bg.canonical_map(pd.concat([prov, recv]).dropna().unique())
    prov = prov.map(lambda r: cmap.get(r, r))
    recv = recv.map(lambda r: cmap.get(r, r))
    print(f"suffixed refs collapsed: {len(cmap):,}")
    w = pd.DataFrame({"prov": prov, "recv": recv, "usd": usd})
    w = w[w.prov.notna()]
    w["gross"] = w.usd.clip(lower=0).fillna(0)
    ident = w.recv.notna()
    print(f"rows with identifiable provider: {len(w):,} "
          f"(identified receiver: {ident.sum():,}; unidentified: {(~ident).sum():,})")
    print(f"gross USD: identified {w.gross[ident].sum()/1e9:,.1f}B, "
          f"unidentified {w.gross[~ident].sum()/1e9:,.1f}B")

    # --- per-funder scale & transparency (all providers, incl. IATI-k-invisible) ---
    fs = pd.DataFrame({
        "txns_ident": w[ident].groupby("prov").size(),
        "txns_unident": w[~ident].groupby("prov").size(),
        "usd_ident": w[ident].groupby("prov").gross.sum(),
        "usd_unident": w[~ident].groupby("prov").gross.sum(),
    }).fillna(0)
    fs["usd_total"] = fs.usd_ident + fs.usd_unident
    fs["transparency"] = np.where(fs.usd_total > 0,
                                  fs.usd_ident / fs.usd_total, np.nan)
    fs.index.name = "ref"
    fs.sort_values("usd_total", ascending=False).to_csv(
        "funder_scale.tsv", sep="\t", float_format="%.2f")
    print(f"funders (providers with any disbursement): {len(fs):,}")
    med = fs[fs.usd_total > 0].transparency.median()
    print(f"median transparency (USD-weighted per funder): {med:.3f}")

    # --- IATI graph: identified arcs (as IATI-k) + per-provider sink arcs ---
    idk = pd.read_csv("graph/arcs_weighted.tsv", sep="\t")
    nodes_k = pd.read_csv("graph/nodes.tsv", sep="\t", header=None,
                          names=["id", "ref"], quoting=3)
    ids = dict(zip(nodes_k.ref, nodes_k.id))
    nxt = len(ids)
    new_rows = []
    un = w[~ident].groupby("prov").agg(count=("gross", "size"),
                                       usd=("gross", "sum"))
    for ref, r in un.iterrows():
        if ref not in ids:
            ids[ref] = nxt
            nxt += 1
        sink = "UNID::" + ref
        ids[sink] = nxt
        nxt += 1
        new_rows.append({"s": ids[ref], "d": ids[sink],
                         "count": int(r["count"]), "usd": round(r.usd, 2)})
    full = pd.concat([idk, pd.DataFrame(new_rows)], ignore_index=True)
    full = full.sort_values(["s", "d"])
    full.to_csv("graph/arcs_full.tsv", sep="\t", index=False)
    with open("graph/nodes_full.tsv", "w") as f:
        for ref, i in sorted(ids.items(), key=lambda kv: kv[1]):
            f.write(f"{i}\t{ref}\n")

    # --- panel ---
    for name, arcs, nn in (("IATI-k", idk, len(nodes_k)), ("IATI", full, nxt)):
        m = len(arcs)
        funders = arcs.s.nunique()
        vol = arcs.usd.clip(lower=0).sum()
        print(f"{name}: n={nn:,} m={m:,} density={m/(nn*(nn-1)):.2e} "
              f"avg deg={m/nn:.3f} gross vol={vol/1e9:,.1f}B funders={funders:,}")


if __name__ == "__main__":
    main()
