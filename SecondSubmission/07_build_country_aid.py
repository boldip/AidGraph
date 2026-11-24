#!/usr/bin/env python3
"""Country-level aid flow network, for a like-for-like H3 comparison with the
COW trade and BIS interbank country networks.

Construction (donor->recipient dyads, standard in the aid literature):
  - rows: type 3, full-row dedup, provider imputed from reporting org.
    NOTE (revised 2026-09-03): the receiver ORGANISATION is deliberately NOT
    required -- the dyad's target is the recipient COUNTRY, which is recorded
    on most rows whether or not the receiving org is identified. The country
    graph therefore belongs to the IATI (full) side of the two-graph design
    and covers ~6x the money of the earlier receiver-identified version;
  - source country: ISO-2 prefix of the provider org ref, or the country of a
    bilateral XM-DAC-<code> agency (official DAC donor codes); multilateral /
    unresolvable providers are dropped (share reported);
  - target country: transaction_recipient_country_code, falling back to the
    activity-level recipient_country_code; rows without either are dropped;
  - self-loops (same country) dropped, consistent with the trade network;
  - weights: transaction count and net USD (same FX table as the org graph).

Output: comparison/aid_country.tsv (+ _nodes.tsv), same format as the other
comparison networks.
"""
import importlib.util
import re

import pandas as pd

spec = importlib.util.spec_from_file_location("bg", "02_build_graph.py")
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)
unwrap, FX, PLACEHOLDER = bg.unwrap, bg.FX, bg.PLACEHOLDER
SECONDARY_REPORTERS = bg.SECONDARY_REPORTERS

ISO2 = set(
    "AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI "
    "BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN "
    "CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK "
    "FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM "
    "HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN "
    "KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK "
    "ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP "
    "NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW "
    "SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF "
    "TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI "
    "VN VU WF WS YE YT ZA ZM ZW".split())

# Official OECD DAC donor codes for bilateral members (multilateral codes,
# 9xx and 4xxxx, deliberately absent -> dropped).
DAC_BILATERAL = {"1": "AT", "2": "BE", "3": "DK", "4": "FR", "5": "DE",
                 "6": "IT", "7": "NL", "8": "NO", "9": "PT", "10": "SE",
                 "11": "CH", "12": "GB", "18": "FI", "20": "IS", "21": "IE",
                 "22": "LU", "301": "CA", "302": "US", "701": "JP",
                 "742": "KR", "801": "AU", "820": "NZ"}


def provider_country(ref):
    m = re.match(r"^XM-DAC-(\d+)", ref)
    if m:
        return DAC_BILATERAL.get(m.group(1))
    m = re.match(r"^([A-Z]{2})-", ref)
    if m and m.group(1) in ISO2:
        return m.group(1)
    return None


def main():
    cols = ["transaction_transaction_type_code", "transaction_provider_org_ref",
            "transaction_receiver_org_ref", "reporting_org_ref",
            "transaction_recipient_country_code", "recipient_country_code",
            "transaction_value", "transaction_value_currency", "default_currency"]
    t3 = pd.read_parquet("Data", columns=cols)
    t3 = t3[t3.transaction_transaction_type_code == "['3']"].drop_duplicates()
    sec = t3.reporting_org_ref.map(unwrap).str.upper().isin(SECONDARY_REPORTERS)
    t3 = t3[~sec]
    print(f"secondary-reporter rows dropped (AidData): {sec.sum():,}")

    prov = t3.transaction_provider_org_ref.map(unwrap)
    prov = prov.fillna(t3.reporting_org_ref.map(unwrap)).str.upper()
    base = prov.notna() & ~bg.is_placeholder(prov)
    t3, prov = t3[base], prov[base]
    print(f"base rows (identifiable provider; receiver org NOT required): {len(t3):,}")

    src = prov.map(provider_country)
    print(f"provider mapped to a country: {src.notna().sum():,} ({src.notna().mean():.1%}) "
          f"(rest: multilateral/unresolvable orgs)")
    dst = t3.transaction_recipient_country_code.map(unwrap).fillna(
        t3.recipient_country_code.map(unwrap)).str.upper()
    dst = dst.where(dst.isin(ISO2))
    print(f"recipient country known: {dst.notna().sum():,} ({dst.notna().mean():.1%})")

    w = pd.DataFrame({"src": src, "dst": dst})
    w["usd"] = t3.transaction_value.map(unwrap).astype(float) * \
        t3.transaction_value_currency.map(unwrap).fillna(
            t3.default_currency.map(unwrap)).map(FX)
    w = w.dropna(subset=["src", "dst"])
    print(f"rows with both countries: {len(w):,}")
    loops = w.src == w.dst
    print(f"same-country rows dropped: {loops.sum():,} "
          f"({w.usd[loops].sum()/w.usd.sum():.1%} of USD)")
    w = w[~loops]
    print(f"rows used: {len(w):,}; net value {w.usd.sum()/1e9:.2f} B USD")

    agg = w.groupby(["src", "dst"]).agg(count=("usd", "size"),
                                        usd=("usd", "sum")).reset_index()
    ids = {c: i for i, c in enumerate(sorted(set(agg.src) | set(agg.dst)))}
    out = pd.DataFrame({"s": agg.src.map(ids), "d": agg.dst.map(ids),
                        "w": agg["count"], "usd": agg.usd.round(2)})
    out.sort_values(["s", "d"]).to_csv("comparison/aid_country.tsv",
                                       sep="\t", index=False)
    with open("comparison/aid_country_nodes.tsv", "w") as f:
        for c, i in sorted(ids.items(), key=lambda kv: kv[1]):
            f.write(f"{i}\t{c}\n")
    print(f"n = {len(ids):,} countries, m = {len(agg):,} arcs -> comparison/aid_country.tsv")


if __name__ == "__main__":
    main()
