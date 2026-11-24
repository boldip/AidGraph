#!/usr/bin/env python3
"""Steps 2-4a: filter to disbursements, resolve endpoints, emit weighted arc list.

Decisions (user-approved 2026-09-02):
  - provider := transaction_provider_org_ref, defaulting to reporting_org_ref when
    missing (IATI standard semantics for disbursements);
  - rows without a receiver ref are dropped (no counterparty recorded);
  - full-row duplicates removed first (matches Elaine's 2,583,194 count);
  - self-loops excluded (counted);
  - arc weights: (a) transaction count, (b) net value in USD at fixed rates.

Outputs (in graph/):
  arclist.txt       - "src<TAB>dst" integer arcs, sorted, unweighted
  arcs_weighted.tsv - "src dst count usd" (usd = net sum, may be negative)
  nodes.tsv         - "id<TAB>ref"
  build_log.txt     - counts for the report

Usage: python3 02_build_graph.py Data
"""
import re
import sys

import pandas as pd

TYPE3 = "['3']"

# Fixed indicative USD rates (2025); crude by design, flagged in the report.
FX = {"USD": 1.0, "USS": 1.0, "GBP": 1.27, "DKK": 0.145, "EUR": 1.08, "XDR": 1.33,
      "CAD": 0.73, "KRW": 0.00073, "UGX": 0.00027, "XOF": 0.0016, "GHS": 0.065,
      "CHF": 1.12, "TZS": 0.00037, "BDT": 0.0084, "SEK": 0.095, "NOK": 0.092,
      "NPR": 0.0075, "NGN": 0.00065, "PKR": 0.0036, "JOD": 1.41, "ETB": 0.0080,
      "KES": 0.0077, "LKR": 0.0033, "XAF": 0.0016, "GNF": 0.000116, "ILS": 0.27,
      "BRL": 0.18}

# Placeholder identifiers that denote a redacted/absent counterparty, not an org.
PLACEHOLDER = {"0", "1", "ANONYMOUS", "EXCLUDED", "NONE", "TBC", "TBD", "N/A",
               "NA", "NULL", "UNKNOWN", "REDACTED", "-", "."}

# v3 (2026-11-18, after the manual audit of the name dictionary): OECD CRS
# channel *category* codes used as organisation references (10000 public
# sector, 21000 international NGO, 22000 donor-country NGO, 61000 private
# sector in provider country, ...; with or without the XM-DAC- prefix) and
# "not available"-type strings denote a class of recipients, not an
# organisation, and are treated as missing references. A code under which an
# organisation itself publishes to IATI (44000 = The World Bank, XM-DAC-43000
# = IMF) is that organisation's identifier and is kept.
GENERIC_REF = re.compile(r"^((XM-DAC-)?\d{2}000|NOT AVAILABLE|NO IDENTIFIER|NOT REGISTERED"
                         r"|NOT APPLICABLE|UNSPECIFIED|OTHER)$")


def publisher_ids():
    import json
    import os
    path = "comparison_data/publisher_names.json"
    return {k.upper() for k in json.load(open(path))} if os.path.exists(path) else set()


def is_placeholder(refs):
    """Boolean mask over a Series of upper-cased refs: placeholders and
    generic category codes (unless an organisation publishes under them)."""
    return refs.isin(PLACEHOLDER) | (refs.str.match(GENERIC_REF, na=False)
                                     & ~refs.isin(publisher_ids()))

# Secondary reporters: publishers that republish OTHER donors' activities.
# Imputing them as provider (and their ISO prefix as donor country) is wrong,
# and their records duplicate primary reporting. AidData republishes World
# Bank projects (activity ids embed WB P-numbers, titles are IBRD/IDA loans,
# $430B) with no provider refs. Their rows are dropped everywhere.
SECONDARY_REPORTERS = {"US-501C3-522318905"}

LISTSTR = re.compile(r"^\[[\"']?(.*?)[\"']?\]$", re.S)

# Suffixed identifiers (Paul, 2026-09-03): some refs are a real org ref plus
# a project suffix, e.g. GB-CHC-229476-WISH2ACTION is a project of IPPF
# (GB-CHC-229476). Conservative rule: strip the suffix ONLY when the base
# ref itself occurs in the data, so genuine refs with internal dashes
# (US-EIN-13-2626135) are never truncated.
SUFFIXED = re.compile(r"^([A-Z]{2}-[A-Z]{2,6}-\d+)-.+$")


# Junk receiver "names" that are placeholders or role descriptions, not orgs
# (v2 narrative column, 2026-09-08).
JUNK_NAME = re.compile(
    r"redact|confidential|not disclosed|not available|anonym|undisclosed"
    r"|^n/?a$|^none$|^nan$|^unknown|^various|^multiple|^tbc$|^tbd$|^\*+$"
    r"|^-+$|miscellaneous|to be determined"
    # v3: category labels and bookkeeping strings used as receiver names
    r"|^correction$|^(international|local|national) ngo$"
    r"|^(ngo|enterprise|government|individual|university|other|public sector|foundation|multilateral)\b.*\b(other|redacted)$"
    r"|^(donor|developing|recipient) country.based ngo$|^private sector in\b|^ngos? based in\b")
WSRE = re.compile(r"\s+")


def norm_name(s):
    return WSRE.sub(" ", s.strip()).casefold() if isinstance(s, str) else None


def name_dictionary(ref, name):
    """name -> ref dictionary: publisher titles plus co-occurrence pairs
    (a name maps to a ref if that ref carries >= 90% of the name's
    ref-bearing rows and >= 3 observations). Co-occurrence beats publishers
    on conflicts. Junk names never enter."""
    import json
    import os
    d = {}
    if os.path.exists("comparison_data/publisher_names.json"):
        for k, v in json.load(open("comparison_data/publisher_names.json")).items():
            n = norm_name(v)
            if n and not JUNK_NAME.search(n):
                d[n] = k.upper()
    both = ref.notna() & name.notna()
    co = pd.DataFrame({"r": ref[both], "n": name[both]}).groupby(
        ["n", "r"]).size().reset_index(name="c")
    tot = co.groupby("n").c.sum()
    best = co.sort_values("c", ascending=False).drop_duplicates("n")
    for _, row in best.iterrows():
        if row.c >= 3 and row.c / tot[row.n] >= 0.9:
            d[row.n] = row.r
    return d


# Registration-number families where a ghost ref one edit from the
# reporter's own ref can only be a typo (charity/company/EIN/KvK numbers).
# Dense semantic code lists (XM-DAC channels, KR-GOV agencies, bare numeric
# World Bank channel codes) are deliberately excluded: there, neighbouring
# codes are real sibling organisations (e.g. 44003 is IFC, not a typo of
# 44000).
REG_FAMILIES = {"CHC", "COH", "CH", "KVK", "EIN", "SC", "BCE", "BCE_KBO",
                "NCB", "ONT", "CVR", "BRC", "CHY", "FC", "COG"}
COUNTRY_PREFIXES = {"GB", "US", "NL", "DK", "NO", "IE", "CA", "AU", "SE",
                    "CH", "BE", "FR", "DE", "FI", "IT", "ES"}


def typo_alias_map(prov, recv, rep):
    """Repair two classes of publisher typos, conservatively.
    (1) wrong/mangled country prefix: <X>-<FAM>-<tail> where a
        <CC>-<FAM>-<tail> with a real country code exists in the data;
    (2) ghost providers one character from the row's own reporting-org ref,
        in registration-number families only, never seen as receiver or
        reporter anywhere."""
    universe = set(pd.concat([prov, recv]).dropna().unique())
    out = {}
    for r in universe:
        m = re.match(r"^([A-Z0-9=]{2,8})[-= ]([A-Z_]{2,7})[-= ](.+)$", r)
        if m and m.group(2) in REG_FAMILIES and m.group(1) not in COUNTRY_PREFIXES:
            for cc in ("GB", "US", "NL", "DK", "NO", "IE"):
                cand = f"{cc}-{m.group(2)}-{m.group(3)}"
                if cand in universe:
                    out[r] = cand
                    break
    recv_u = set(recv.dropna())
    rep_u = set(rep.dropna())
    ghosts = (prov.notna() & rep.notna() & (prov != rep)
              & ~prov.isin(recv_u) & ~prov.isin(rep_u))
    fam = re.compile(r"^[A-Z]{2}[-=][A-Z_]{2,7}[-= ]")
    for p, q in pd.DataFrame({"p": prov[ghosts], "q": rep[ghosts]}
                             ).drop_duplicates().itertuples(index=False):
        if p in out or len(p) != len(q):
            continue
        mm = re.match(r"^[A-Z]{2}[-=]([A-Z_]{2,7})[-= ]", p)
        if not mm or mm.group(1) not in REG_FAMILIES:
            continue
        if sum(a != b for a, b in zip(p, q)) == 1:
            out[p] = q
    return out


def canonical_map(refs):
    """Map suffixed refs to their base ref when the base exists in `refs`."""
    universe = set(refs)
    out = {}
    for r in universe:
        m = SUFFIXED.match(r) if isinstance(r, str) else None
        if m and m.group(1) in universe:
            out[r] = m.group(1)
    return out


def unwrap(s):
    """Strip the single-element stringified-list wrapper: ['x'], [\"x\"] or [1.0]."""
    if not isinstance(s, str):
        return None
    m = LISTSTR.match(s)
    return (m.group(1) if m else s).strip() or None


def load_rows(path, say=print):
    """Disbursement rows: type 3, full-row dedup, secondary reporters removed."""
    df = pd.read_parquet(path)
    say(f"total rows: {len(df):,}")
    t3 = df[df.transaction_transaction_type_code == TYPE3]
    say(f"type-3 (disbursement) rows: {len(t3):,}")
    t3 = t3.drop_duplicates()
    say(f"after full-row dedup: {len(t3):,} (Elaine: 2,583,194)")
    sec = t3.reporting_org_ref.map(unwrap).str.upper().isin(SECONDARY_REPORTERS)
    t3 = t3[~sec]
    say(f"secondary-reporter rows dropped (AidData et al.): {sec.sum():,}")
    return t3


def resolve_rows(t3, say=print):
    """Endpoint resolution on the disbursement rows (the pipeline of the
    paper's Methods): returns a DataFrame aligned with t3's index with
    columns prov, recv, val, cur, imputed; rows lacking an endpoint or
    forming a self-loop are already removed. Shared by 02 (graph build)
    and 11a (humanitarian flags), so the two can never diverge."""
    # Identity is the case-normalised ref: case variants of the same identifier
    # (e.g. XM-DAC-3-1 vs xm-dac-3-1) are the same organisation.
    prov = t3.transaction_provider_org_ref.map(unwrap)
    imputed = prov.isna()
    prov = prov.fillna(t3.reporting_org_ref.map(unwrap)).str.upper()
    recv = t3.transaction_receiver_org_ref.map(unwrap).str.upper()
    gen = recv.str.match(GENERIC_REF, na=False) & ~recv.isin(publisher_ids())
    say(f"receiver refs that are generic category codes or placeholder strings, "
        f"treated as missing: {gen.sum():,} rows, {recv[gen].nunique()} distinct codes "
        f"(codes kept because an organisation publishes under them: "
        f"{sorted(k for k in publisher_ids() if GENERIC_REF.match(k))})")
    prov = prov.where(~is_placeholder(prov))
    recv = recv.where(~is_placeholder(recv))
    tmap = typo_alias_map(prov, recv,
                          t3.reporting_org_ref.map(unwrap).str.upper())
    say(f"typo aliases repaired (wrong prefix / ghost one-off): {len(tmap):,}")
    prov = prov.map(lambda r: tmap.get(r, r))
    recv = recv.map(lambda r: tmap.get(r, r))
    # v2 (2026-09-08): resolve ref-less receivers via the name dictionary
    if "transaction_receiver_org_narrative" in t3.columns:
        rname = t3.transaction_receiver_org_narrative.map(unwrap).map(norm_name)
        rname = rname.where(rname.notna()
                            & ~rname.str.contains(JUNK_NAME, na=False))
        d = name_dictionary(recv, rname)
        say(f"name->ref dictionary entries: {len(d):,}")
        fill = recv.isna() & rname.notna()
        resolved = rname[fill].map(d)
        recv = recv.where(recv.notna(), resolved)
        say(f"ref-less receivers resolved by name dictionary: "
            f"{resolved.notna().sum():,} rows "
            f"(unmatched named rows stay dropped: {(fill & resolved.isna()).sum():,})")
    cmap = canonical_map(pd.concat([prov, recv]).dropna().unique())
    say(f"suffixed refs collapsed onto existing base refs: {len(cmap):,}")
    prov = prov.map(lambda r: cmap.get(r, r))
    recv = recv.map(lambda r: cmap.get(r, r))
    val = t3.transaction_value.map(unwrap).astype(float)
    cur = t3.transaction_value_currency.map(unwrap).fillna(
        t3.default_currency.map(unwrap))

    w = pd.DataFrame({"prov": prov, "recv": recv, "val": val, "cur": cur,
                      "imputed": imputed})
    w = w[w.recv.notna() & w.prov.notna()]
    say(f"rows with both endpoints: {len(w):,} "
        f"(provider imputed from reporting org on {w.imputed.sum():,} of them)")
    loops = w.prov == w.recv
    say(f"self-loop rows dropped: {loops.sum():,}")
    w = w[~loops].copy()
    say(f"rows used for arcs: {len(w):,}")
    return w


def main(path):
    log = []

    def say(msg):
        print(msg)
        log.append(msg)

    t3 = load_rows(path, say)
    w = resolve_rows(t3, say)
    del t3

    w["usd"] = w.val * w.cur.map(FX)
    nofx = w.usd.isna()
    if nofx.any():
        say(f"rows without FX rate (excluded from USD weight only): {nofx.sum():,}")
        w.loc[nofx, "usd"] = 0.0
    say(f"total net disbursement value: {w.usd.sum()/1e9:,.2f} B USD "
        f"(negative-value rows: {(w.val < 0).sum():,})")

    orgs = pd.concat([w.prov, w.recv]).unique()
    ids = {r: i for i, r in enumerate(sorted(orgs))}
    say(f"n = {len(ids):,} nodes")
    w["s"] = w.prov.map(ids)
    w["d"] = w.recv.map(ids)
    agg = w.groupby(["s", "d"]).agg(count=("val", "size"),
                                    usd=("usd", "sum")).reset_index()
    agg = agg.sort_values(["s", "d"])
    say(f"m = {len(agg):,} distinct arcs")
    say(f"arcs with negative net USD value: {(agg.usd < 0).sum():,}")

    import os
    os.makedirs("graph", exist_ok=True)
    agg[["s", "d"]].to_csv("graph/arclist.txt", sep="\t", index=False, header=False)
    agg.to_csv("graph/arcs_weighted.tsv", sep="\t", index=False,
               float_format="%.2f")
    with open("graph/nodes.tsv", "w") as f:
        for r, i in sorted(ids.items(), key=lambda kv: kv[1]):
            f.write(f"{i}\t{r}\n")
    with open("graph/build_log.txt", "w") as f:
        f.write("\n".join(log) + "\n")
    say("wrote graph/arclist.txt, graph/arcs_weighted.tsv, graph/nodes.tsv")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Data")
