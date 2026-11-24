#!/usr/bin/env python3
"""Build comparison-network edge lists for the H3 table. See SOURCES.md for
full provenance. Raw files are downloaded into comparison_data/ (gitignored)
if absent; derived edge lists go to comparison/{airline,trade,interbank}.tsv
with columns s, d, w and a matching *_nodes.tsv id->label map.

Networks:
  airline   OpenFlights routes: airports, arc = at least one scheduled route,
            w = number of operating airlines on the route.
  trade     COW Dyadic Trade v4.0, year 2014: countries, arc exporter->importer,
            w = import flow in millions of current USD.
  interbank BIS Consolidated Banking Statistics, 2025-Q4: countries, arc
            reporter->counterparty, w = total claims of reporter's domestic
            banks (4R) on counterparty-country BANKS, ultimate risk basis,
            millions USD. (True bank-level interbank networks are
            confidential; this country-level layer is the standard public
            proxy, cf. Minoiu & Reyes 2013.)
"""
import os
import re
import subprocess
import sys

import pandas as pd

RAW = "comparison_data"
OUT = "comparison"

URLS = {
    "routes.dat": "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat",
    "COW_Trade_4.0.zip": "https://correlatesofwar.org/wp-content/uploads/COW_Trade_4.0.zip",
    "WS_CBS_PUB_csv_flat.zip": "https://data.bis.org/static/bulk/WS_CBS_PUB_csv_flat.zip",
}

BIS_QUARTER = "2025-Q4"
COW_YEAR = 2014


def fetch(name):
    path = os.path.join(RAW, name)
    if not os.path.exists(path):
        subprocess.run(["curl", "-sL", "--max-time", "600", "-o", path,
                        URLS[name]], check=True)
    return path


def write(name, arcs, labels):
    """arcs: DataFrame with src,dst (labels), w. Writes ids + node map."""
    ids = {l: i for i, l in enumerate(sorted(labels))}
    df = pd.DataFrame({"s": arcs.src.map(ids), "d": arcs.dst.map(ids),
                       "w": arcs.w}).sort_values(["s", "d"])
    df.to_csv(f"{OUT}/{name}.tsv", sep="\t", index=False)
    with open(f"{OUT}/{name}_nodes.tsv", "w") as f:
        for l, i in sorted(ids.items(), key=lambda kv: kv[1]):
            f.write(f"{i}\t{l}\n")
    print(f"{name}: n = {len(ids):,}, m = {len(df):,}, W = {df.w.sum():,.0f}")


def airline():
    r = pd.read_csv(fetch("routes.dat"), header=None, na_values="\\N",
                    names=["airline", "airline_id", "src", "src_id",
                           "dst", "dst_id", "codeshare", "stops", "equip"])
    r = r.dropna(subset=["src", "dst"])
    r = r[r.src != r.dst]
    agg = r.groupby(["src", "dst"]).size().reset_index(name="w")
    write("airline", agg, set(agg.src) | set(agg.dst))


def trade():
    z = fetch("COW_Trade_4.0.zip")
    subprocess.run(["unzip", "-o", "-q", z, "COW_Trade_4.0/Dyadic_COW_4.0.csv",
                    "-d", RAW], check=True)
    d = pd.read_csv(f"{RAW}/COW_Trade_4.0/Dyadic_COW_4.0.csv",
                    usecols=["importer1", "importer2", "year", "flow1", "flow2"])
    d = d[d.year == COW_YEAR]
    # flow1 = imports of country1 from country2 => arc c2 -> c1, and vice versa
    a = pd.concat([
        d.rename(columns={"importer2": "src", "importer1": "dst", "flow1": "w"})[["src", "dst", "w"]],
        d.rename(columns={"importer1": "src", "importer2": "dst", "flow2": "w"})[["src", "dst", "w"]],
    ])
    a = a[a.w > 0]  # -9 encodes missing; 0 is no recorded trade
    write("trade", a, set(a.src) | set(a.dst))


def interbank():
    raw = f"{RAW}/bis_interbank_raw.tsv"
    if not os.path.exists(raw):
        z = fetch("WS_CBS_PUB_csv_flat.zip")
        subprocess.run(["unzip", "-o", "-q", z, "-d", RAW], check=True)
        cols = {"L_MEASURE:Measure": "meas", "L_REP_CTY:Reporting country": "rep",
                "CBS_BANK_TYPE:CBS bank type": "bt",
                "CBS_BASIS:CBS reporting basis": "basis",
                "L_POSITION:Balance sheet position": "pos",
                "L_INSTR:Type of instruments": "instr",
                "REM_MATURITY:Remaining maturity": "mat",
                "CURR_TYPE_BOOK:Currency type of booking location": "cur",
                "L_CP_SECTOR:Counterparty sector": "cps",
                "L_CP_COUNTRY:Counterparty country": "cp",
                "TIME_PERIOD:Time period or range": "time",
                "OBS_VALUE:Observation Value": "val"}
        out = []
        for ch in pd.read_csv(f"{RAW}/WS_CBS_PUB_csv_flat.csv",
                              chunksize=2_000_000, dtype=str,
                              usecols=list(cols)):
            ch = ch.rename(columns=cols)
            f = ch[ch.meas.str.startswith("S:") & ch.bt.str.startswith("4R:")
                   & ch.basis.str.startswith("U:") & ch.pos.str.startswith("C:")
                   & ch.instr.str.startswith("A:") & ch.mat.str.startswith("A:")
                   & ch.cur.str.startswith("TO1:") & ch.cps.str.startswith("B:")]
            if len(f):
                out.append(f[["rep", "cp", "time", "val"]])
        pd.concat(out).to_csv(raw, sep="\t", index=False)
    b = pd.read_csv(raw, sep="\t", dtype=str)
    b = b[b.time == BIS_QUARTER].copy()
    b["src"] = b.rep.str.extract(r"^([A-Z0-9]+):")[0]
    b["dst"] = b.cp.str.extract(r"^([A-Z0-9]+):")[0]
    iso2 = re.compile(r"^[A-Z]{2}$")
    b = b[b.src.str.match(iso2) & b.dst.str.match(iso2)]
    b["w"] = pd.to_numeric(b.val, errors="coerce")
    b = b[(b.w > 0) & (b.src != b.dst)]
    agg = b.groupby(["src", "dst"]).w.sum().reset_index()
    write("interbank", agg, set(agg.src) | set(agg.dst))


if __name__ == "__main__":
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    for net in (sys.argv[1:] or ["airline", "trade", "interbank"]):
        {"airline": airline, "trade": trade, "interbank": interbank}[net]()
