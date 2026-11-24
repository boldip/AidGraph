#!/usr/bin/env python3
"""Two further comparison networks in search of close matches to iati-cty
(see Table "provenance" in the report for full provenance):

  refugee  UNHCR refugee population 2024: arc origin country -> country of
           asylum, w = number of refugees (incl. people in refugee-like
           situations) hosted at end-2024. Source: UNHCR Refugee Data
           Finder population API (api.unhcr.org/population/v1), retrieved
           2026-09-03. Observational; ISO-3 country codes.

  remit    KNOMAD / World Bank bilateral remittance matrix 2021: arc
           sending country -> receiving country, w = estimated remittance
           flow in millions of USD. CAVEAT: model-based estimates derived
           from migrant stocks and incomes (Ratha-Shaw method), not
           observed transfers; retrieved 2026-09-03 via the Internet
           Archive copy of knomad.org.

Raw files expected in comparison_data/ (unhcr_2024.json, remit_2021.xlsx).
Outputs comparison/{refugee,remit}.tsv (+ _nodes.tsv), same format as the
other comparison networks.
"""
import json

import pandas as pd


def write(name, arcs, labels):
    ids = {l: i for i, l in enumerate(sorted(labels))}
    df = pd.DataFrame({"s": arcs.src.map(ids), "d": arcs.dst.map(ids),
                       "w": arcs.w}).sort_values(["s", "d"])
    df.to_csv(f"comparison/{name}.tsv", sep="\t", index=False)
    with open(f"comparison/{name}_nodes.tsv", "w") as f:
        for l, i in sorted(ids.items(), key=lambda kv: kv[1]):
            f.write(f"{i}\t{l}\n")
    print(f"{name}: n = {len(ids):,}, m = {len(df):,}, W = {df.w.sum():,.0f}")


def refugee():
    rows = json.load(open("comparison_data/unhcr_2024.json"))
    df = pd.DataFrame(rows)
    df["w"] = pd.to_numeric(df.refugees, errors="coerce").fillna(0)
    df = df[(df.w > 0) & df.coo_iso.notna() & df.coa_iso.notna()]
    df = df[df.coo_iso.str.len() == 3]
    df = df[df.coa_iso.str.len() == 3]
    # UNK/unknown pseudo-origins
    df = df[~df.coo_iso.isin({"UNK", "STA"}) & ~df.coa_iso.isin({"UNK", "STA"})]
    df = df[df.coo_iso != df.coa_iso]
    agg = df.groupby(["coo_iso", "coa_iso"]).w.sum().reset_index()
    agg.columns = ["src", "dst", "w"]
    write("refugee", agg, set(agg.src) | set(agg.dst))


def remit():
    raw = pd.read_excel("comparison_data/remit_2021.xlsx",
                        sheet_name=0, header=None)
    # row 0: title; row 1: receiving countries from col 1; col 0 from row 2:
    # sending countries. Find the layout dynamically.
    hdr_row = None
    for i in range(4):
        if str(raw.iloc[i, 0]).strip().startswith("Remittance-receiving"):
            hdr_row = i
            break
    recv = raw.iloc[hdr_row, 1:].tolist()
    body = raw.iloc[hdr_row + 1:].reset_index(drop=True)
    out = []
    for _, r in body.iterrows():
        snd = str(r.iloc[0]).strip()
        if not snd or snd.lower().startswith(("nan", "world", "total")):
            continue
        for j, rcv in enumerate(recv, start=1):
            rcv = str(rcv).strip()
            if not rcv or rcv.lower().startswith(("nan", "world", "total")):
                continue
            v = pd.to_numeric(r.iloc[j], errors="coerce")
            if pd.notna(v) and v > 0 and snd != rcv:
                out.append((snd, rcv, float(v)))
    arcs = pd.DataFrame(out, columns=["src", "dst", "w"])
    write("remit", arcs, set(arcs.src) | set(arcs.dst))


if __name__ == "__main__":
    refugee()
    remit()
