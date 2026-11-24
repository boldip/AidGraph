#!/usr/bin/env python3
"""The iati-k+1 variant (Paul's suggestion 3, 2026-09-03): augment the
payer-reported disbursement graph with receiver-reported incoming funds.

Type-1 (incoming funds) rows are the receiver's record: the reporting org
IS the receiver, and transaction_provider_org_ref names the payer. Arcs
provider -> reporting org are added for rows with a named provider.

Double counting (the reason mail1 excluded incoming funds from a mixed
graph) is handled by construction:
  - topology: arc-set union, an arc reported by both sides is one arc;
  - weights: payer-reported (type-3) count/USD kept wherever the arc exists
    in iati-k; type-1 weights used only for arcs unseen in type 3.

Same hygiene as iati-k: full-row dedup, secondary reporters censored,
placeholders dropped, refs uppercased and suffix-canonicalised, self-loops
dropped. Outputs graph/arcs_kplus1.tsv (+ nodes_kplus1.tsv) with a
`src_type` column (3 = payer-reported, 1 = receiver-only).
"""
import importlib.util

import pandas as pd

spec = importlib.util.spec_from_file_location("bg", "02_build_graph.py")
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)


def main():
    t = pd.read_parquet("Data")
    t1 = t[t.transaction_transaction_type_code == "['1']"].drop_duplicates()
    del t
    sec = t1.reporting_org_ref.map(bg.unwrap).str.upper().isin(
        bg.SECONDARY_REPORTERS)
    t1 = t1[~sec]
    print(f"type-1 dedup rows: {len(t1):,} (secondary reporters: {sec.sum():,})")

    prov = t1.transaction_provider_org_ref.map(bg.unwrap).str.upper()
    recv = t1.reporting_org_ref.map(bg.unwrap).str.upper()
    prov = prov.where(~prov.isin(bg.PLACEHOLDER))
    recv = recv.where(~recv.isin(bg.PLACEHOLDER))
    usd = (t1.transaction_value.map(bg.unwrap).astype(float)
           * t1.transaction_value_currency.map(bg.unwrap)
             .fillna(t1.default_currency.map(bg.unwrap)).map(bg.FX))

    k = pd.read_csv("graph/arcs_weighted.tsv", sep="\t")
    nodes_k = pd.read_csv("graph/nodes.tsv", sep="\t", header=None,
                          names=["id", "ref"], quoting=3)
    # canonicalise type-1 refs against the union universe
    universe = pd.concat([prov, recv, nodes_k.ref]).dropna().unique()
    cmap = bg.canonical_map(universe)
    prov = prov.map(lambda r: cmap.get(r, r))
    recv = recv.map(lambda r: cmap.get(r, r))

    w = pd.DataFrame({"prov": prov, "recv": recv, "usd": usd})
    w = w[w.prov.notna() & w.recv.notna() & (w.prov != w.recv)]
    print(f"usable type-1 rows (named provider, no self-loop): {len(w):,}")
    t1arcs = w.assign(gross=w.usd.clip(lower=0).fillna(0)).groupby(
        ["prov", "recv"]).agg(count=("usd", "size"),
                              usd=("gross", "sum")).reset_index()
    print(f"distinct type-1 arcs: {len(t1arcs):,}")

    ids = dict(zip(nodes_k.ref, nodes_k.id))
    nxt = len(ids)
    for r in pd.concat([t1arcs.prov, t1arcs.recv]).unique():
        if r not in ids:
            ids[r] = nxt
            nxt += 1
    t1arcs["s"] = t1arcs.prov.map(ids)
    t1arcs["d"] = t1arcs.recv.map(ids)

    known = set(zip(k.s, k.d))
    new = t1arcs[[(s, d) not in known for s, d in zip(t1arcs.s, t1arcs.d)]]
    both = len(t1arcs) - len(new)
    print(f"type-1 arcs already payer-reported (weights kept from type 3): {both:,}")
    print(f"type-1-only arcs added: {len(new):,}")

    full = pd.concat([k.assign(src_type=3),
                      new[["s", "d", "count", "usd"]].assign(src_type=1)],
                     ignore_index=True).sort_values(["s", "d"])
    full.to_csv("graph/arcs_kplus1.tsv", sep="\t", index=False,
                float_format="%.2f")
    with open("graph/nodes_kplus1.tsv", "w") as f:
        for ref, i in sorted(ids.items(), key=lambda kv: kv[1]):
            f.write(f"{i}\t{ref}\n")
    n = nxt
    m = len(full)
    newf = set(new.s) - set(k.s)
    print(f"iati-k+1: n={n:,} (+{n-len(nodes_k):,}), m={m:,} (+{m-len(k):,}), "
          f"funders {full.s.nunique():,} ({len(newf):,} new, "
          f"USAID present: {'US-GOV-1' in [r for r,i in ids.items() if i in newf] or ids.get('US-GOV-1') in set(full.s)})")


if __name__ == "__main__":
    main()
