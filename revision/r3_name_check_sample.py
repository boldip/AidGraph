#!/usr/bin/env python3
"""Reviewer 2, point 3: a manual check sample of the receiver-name resolution.

Rebuilds the name -> ref dictionary exactly as 02_build_graph.py does
(publisher registry titles + co-occurrence pairs with >= 3 observations and
>= 90% dominance), applies it to the type-3 rows whose receiver has a name
but no ref, and writes:
  name_check_sample.xlsx / .tsv : 100 resolved (name, ref) pairs drawn
      uniformly at random (seed 2026) plus the 30 pairs resolving the most
      rows, with the registry title of the target ref, the dictionary source
      and the co-occurrence support, and an empty 'verdict' column.
  name_check_summary.md : counts.
"""
import importlib.util, json, os, sys
import numpy as np, pandas as pd
BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))
spec = importlib.util.spec_from_file_location("b", f"{BASE}/02_build_graph.py"); B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
os.chdir(BASE)  # name_dictionary reads comparison_data/publisher_names.json relatively
cols = ["transaction_transaction_type_code", "reporting_org_ref", "transaction_provider_org_ref",
        "transaction_receiver_org_ref", "transaction_receiver_org_narrative", "transaction_value", "iati_identifier"]
df = pd.read_parquet("Data", columns=cols)
t3 = df[df.transaction_transaction_type_code == B.TYPE3].drop_duplicates()
sec = t3.reporting_org_ref.map(B.unwrap).str.upper().isin(B.SECONDARY_REPORTERS); t3 = t3[~sec]
recv = t3.transaction_receiver_org_ref.map(B.unwrap).str.upper(); recv = recv.where(~recv.isin(B.PLACEHOLDER))
raw = t3.transaction_receiver_org_narrative.map(B.unwrap)
rname = raw.map(B.norm_name); rname = rname.where(rname.notna() & ~rname.str.contains(B.JUNK_NAME, na=False))
d = B.name_dictionary(recv, rname)
pub = {k.upper(): v for k, v in json.load(open("comparison_data/publisher_names.json")).items()}
pubnames = {B.norm_name(v) for v in pub.values()}
both = recv.notna() & rname.notna()
co = pd.DataFrame({"r": recv[both], "n": rname[both]}).groupby(["n", "r"]).size().reset_index(name="c")
tot = co.groupby("n").c.sum(); best = co.sort_values("c", ascending=False).drop_duplicates("n").set_index("n")
fill = recv.isna() & rname.notna()
res = pd.DataFrame({"name": rname[fill], "raw": raw[fill], "reporter": t3.reporting_org_ref[fill].map(B.unwrap).str.upper(),
                    "value": t3.transaction_value[fill].map(B.unwrap).astype(float)})
res["ref"] = res.name.map(d); res = res[res.ref.notna()]
pairs = res.groupby(["name", "ref"]).agg(rows=("raw", "size"), raw_example=("raw", "first"), reporters=("reporter", "nunique"),
                                         reporter_example=("reporter", "first")).reset_index()
pairs["registry_title_of_ref"] = pairs.ref.map(pub)
pairs["source"] = np.where(pairs.name.isin(best.index) & (pairs.name.map(lambda x: best.c.get(x, 0)) >= 3), "co-occurrence", "publisher title")
pairs["cooc_support_rows"] = pairs.name.map(lambda x: int(best.c.get(x, 0)))
pairs["cooc_dominance"] = pairs.name.map(lambda x: best.c.get(x, 0) / tot.get(x, np.nan) if x in tot.index else np.nan)
pairs["ref_also_reporter_of_row"] = pairs.apply(lambda r: r.ref == r.reporter_example, axis=1)
rng = np.random.default_rng(2026)
samp = pairs.iloc[rng.choice(len(pairs), size=100, replace=False)].assign(stratum="random 100")
top = pairs.nlargest(30, "rows").assign(stratum="top 30 by rows")
out = pd.concat([samp, top]).drop_duplicates(subset=["name", "ref"], keep="last")
out["verdict (correct / wrong / unsure)"] = ""
cols_out = ["stratum", "raw_example", "name", "ref", "registry_title_of_ref", "source", "cooc_support_rows", "cooc_dominance", "rows", "reporters",
            "reporter_example", "ref_also_reporter_of_row", "verdict (correct / wrong / unsure)"]
out = out[cols_out]
os.chdir(os.path.dirname(os.path.abspath(__file__)))
out.to_csv("name_check_sample.tsv", sep="\t", index=False)
with pd.ExcelWriter("name_check_sample.xlsx", engine="openpyxl") as xw:
    out.to_excel(xw, index=False, sheet_name="sample")
    ws = xw.sheets["sample"]
    for c, w in zip("ABCDEFGHIJKLM", [14, 50, 40, 26, 44, 16, 10, 10, 8, 8, 20, 10, 24]): ws.column_dimensions[c].width = w
    ws.freeze_panes = "A2"
md = ["# Receiver-name resolution: check sample", "",
      f"- dictionary entries: {len(d):,}", f"- ref-less named receiver rows resolved: {len(res):,}, distinct (name, ref) pairs: {len(pairs):,}",
      f"- pairs from publisher titles: {(pairs.source=='publisher title').sum():,}; from co-occurrence: {(pairs.source=='co-occurrence').sum():,}",
      f"- top 30 pairs account for {top.rows.sum()/len(res):.1%} of resolved rows; top 100 for {pairs.nlargest(100,'rows').rows.sum()/len(res):.1%}",
      f"- resolved rows where the target ref is the reporting organisation itself (internal transfer, dropped as self-loop later): {res[res.ref==res.reporter].shape[0]:,}", "",
      "Sample: 100 pairs uniformly at random (seed 2026) + the 30 pairs resolving the most rows, in name_check_sample.xlsx with an empty verdict column."]
open("name_check_summary.md", "w").write("\n".join(md)); print("\n".join(md))
