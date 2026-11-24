#!/usr/bin/env python3
"""Enrich name_check_sample.xlsx with the evidence needed to judge each
(name, ref) pair by hand, plus an automatic hint. Writes
name_check_audit.xlsx (sheet 'sample', verdict column last, still empty,
plus a 'how_to' sheet). The sample itself is unchanged (same 128 pairs).

Added columns
  other_names_seen_with_ref : the receiver names that co-occur with this ref
                              in rows carrying both name and ref (top 4, with
                              row counts). If they all describe the same
                              organisation as `raw_example`, the pair is right.
  reporter_example_title    : registry title of the reporter in reporter_example
  lookup_url                : registry page for the ref (by prefix)
  auto_hint                 : what the heuristics see
  suggested_verdict         : correct / wrong / check  (a suggestion only)
"""
import difflib, importlib.util, json, os, re
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(HERE, "..", "SecondSubmission"))
spec = importlib.util.spec_from_file_location("b", f"{BASE}/02_build_graph.py"); B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
os.chdir(BASE)
cols = ["transaction_transaction_type_code", "reporting_org_ref", "transaction_provider_org_ref",
        "transaction_receiver_org_ref", "transaction_receiver_org_narrative", "transaction_value", "iati_identifier"]  # same as r3, so drop_duplicates is identical
df = pd.read_parquet("Data", columns=cols)
t3 = df[df.transaction_transaction_type_code == B.TYPE3].drop_duplicates()
sec = t3.reporting_org_ref.map(B.unwrap).str.upper().isin(B.SECONDARY_REPORTERS); t3 = t3[~sec]
recv = t3.transaction_receiver_org_ref.map(B.unwrap).str.upper(); recv = recv.where(~recv.isin(B.PLACEHOLDER))
raw = t3.transaction_receiver_org_narrative.map(B.unwrap)
rname = raw.map(B.norm_name)
both = recv.notna() & rname.notna()
co = pd.DataFrame({"r": recv[both], "n": rname[both], "raw": raw[both]}).groupby(["r", "n"]).agg(c=("raw", "size"), raw=("raw", "first")).reset_index()
co = co.sort_values(["r", "c"], ascending=[True, False])
pub = {k.upper(): v for k, v in json.load(open("comparison_data/publisher_names.json")).items()}
GENERIC_REF = re.compile(r"^((XM-DAC-)?\d{2}000|NOT AVAILABLE|NO IDENTIFIER|NOT REGISTERED|NOT APPLICABLE|UNSPECIFIED|OTHER)$")
rname_j = rname.where(rname.notna() & ~rname.str.contains(B.JUNK_NAME, na=False))
d = B.name_dictionary(recv, rname_j)
fill = recv.isna() & rname_j.notna()
res = pd.DataFrame({"name": rname_j[fill]}); res["ref"] = res.name.map(d); res = res[res.ref.notna()]
# which pairs were in the uniform random draw (r3 kept overlapping pairs under the top-30 stratum)
pairs_r3 = res.groupby(["name", "ref"]).size().reset_index(name="rows")
assert len(pairs_r3) == 2174, len(pairs_r3)
rng = np.random.default_rng(2026)
rand_pairs = set(map(tuple, pairs_r3.iloc[rng.choice(len(pairs_r3), size=100, replace=False)][["name", "ref"]].to_numpy()))
gen = res.ref.str.match(GENERIC_REF)
pairs_all = res.groupby(["name", "ref"]).size().reset_index(name="rows")
gen_pairs = pairs_all[pairs_all.ref.str.match(GENERIC_REF)]
gen_summary = [f"- resolved rows whose target ref is a generic CRS channel code or placeholder: {int(gen.sum()):,} of {len(res):,} ({gen.mean():.2%}), in {len(gen_pairs):,} of {len(pairs_all):,} pairs",
               "- by target: " + "; ".join(f"{r.ref} {r.rows:,} rows/{r.pairs} pairs" for r in gen_pairs.groupby("ref").agg(rows=("rows","sum"), pairs=("rows","size")).reset_index().sort_values("rows", ascending=False).itertuples())]
print("\n".join(gen_summary))
os.chdir(HERE)
open("name_check_summary.md", "a").write("\n\nGeneric targets (r6_name_check_enrich.py):\n" + "\n".join(gen_summary) + "\n")

s = pd.read_excel("name_check_sample.xlsx")
VERD = s.columns[-1]

def others(ref, name):
    sub = co[(co.r == ref) & (co.n != name)].head(4)
    return "; ".join(f"{r.raw.strip()} ({r.c})" for r in sub.itertuples()) if len(sub) else ""

def url(ref):
    m = re.match(r"^US-(EIN|IRS)-(\d{2})-?(\d{7})$", ref)
    if m: return f"https://projects.propublica.org/nonprofits/organizations/{m.group(2)}{m.group(3)}"
    m = re.match(r"^GB-CHC-(\d+)$", ref)
    if m: return f"https://register-of-charities.charitycommission.gov.uk/charity-search/-/results/page/1/delta/20/keywords/{m.group(1)}"
    m = re.match(r"^GB-COH-(\w+)$", ref)
    if m: return f"https://find-and-update.company-information.service.gov.uk/company/{m.group(1)}"
    m = re.match(r"^GB-SC-(SC\d+)$", ref)
    if m: return f"https://www.oscr.org.uk/about-charities/search-the-register/charity-details?number={m.group(1)}"
    m = re.match(r"^NL-KVK-(\d+)$", ref)
    if m: return f"https://www.kvk.nl/zoeken/?q={m.group(1)}"
    m = re.match(r"^XM-DAC-(\d{5})$", ref)
    if m: return f"https://iatiregistry.org/publisher/?q={ref}  (CRS channel code {m.group(1)}: https://codelists.iatistandard.org/CRSChannelCode/)"
    return f"https://iatiregistry.org/publisher/?q={ref}"

def sim(a, b):
    if not isinstance(b, str): return np.nan
    na, nb = B.norm_name(a) or "", B.norm_name(b) or ""
    na = re.sub(r"\(.*?\)", "", na); nb = re.sub(r"\(.*?\)", "", nb)
    ta, tb = set(na.split()), set(nb.split())
    jac = len(ta & tb) / max(1, len(ta | tb))
    return max(jac, difflib.SequenceMatcher(None, na, nb).ratio())

GENERIC_NAME = re.compile(r"^(international ngo|correction|enterprise.*other|other|ngo|various|multiple|n/?a|unknown|individual.*|local ngo|government.*other|donor government|private sector.*|.*not (specified|available).*)$", re.I)

hints, sugg = [], []
for r in s.itertuples():
    h = []; v = "check"
    ref = str(r.ref); name = str(r.name)
    if GENERIC_REF.match(ref):
        h.append("ref is a generic category code or placeholder, not an organisation"); v = "wrong"
    if GENERIC_NAME.match(name.strip()):
        h.append("name is a generic label, not an organisation"); v = "wrong"
    if re.match(r"^[A-Z0-9 .-]+$", ref) and "-" not in ref and not ref.isdigit():
        h.append("ref is an acronym the reporter made up, not a registered identifier (the node exists in the graph under this string)")
    if ref.isdigit() and not GENERIC_REF.match(ref):
        h.append("bare numeric ref: a CRS channel code of a specific organisation, or a reporter's internal number")
    if re.match(r"^XM-DAC-\d{5}-", ref):
        h.append("ref is a reporter-specific sub-identifier (vendor/partner code of a UN agency); check that the code is used only for this organisation")
    sc = sim(r.raw_example, r.registry_title_of_ref)
    if not np.isnan(sc):
        if sc >= 0.6:
            h.append(f"registry title matches the name (similarity {sc:.2f})")
            if v == "check": v = "correct"
        elif sc >= 0.35: h.append(f"registry title only partly matches (similarity {sc:.2f}): same organisation, affiliate, or different entity?")
        else: h.append(f"registry title does not match the name literally (similarity {sc:.2f}): acronym, or a different entity?")
    else:
        h.append("ref is not an IATI publisher: judge from the names seen with the ref and from the registry link")
    if r.cooc_dominance < 1.0 and not np.isnan(r.cooc_dominance):
        h.append(f"co-occurrence dominance {r.cooc_dominance:.2f} (other refs also seen with this name)")
    if r.ref_also_reporter_of_row:
        h.append("resolved ref equals the reporter: internal transfer, dropped later as a self-loop")
    hints.append("; ".join(h)); sugg.append(v)

out = s.drop(columns=[VERD]).copy()
out["in_random_sample"] = [(r.name, r.ref) in rand_pairs for r in s.itertuples()]
assert out.in_random_sample.sum() == 100, out.in_random_sample.sum()
out["other_names_seen_with_ref"] = [others(r.ref, r.name) for r in s.itertuples()]
out["reporter_example_title"] = s.reporter_example.map(pub)
out["lookup_url"] = s.ref.map(url)
out["auto_hint"] = hints
out["suggested_verdict"] = sugg
out[VERD] = ""
out["note"] = ""
print(out.suggested_verdict.value_counts())
print(out.groupby(["stratum", "suggested_verdict"]).size())

howto = pd.DataFrame({"how to audit": [
 "Goal: for every row decide whether the receiver NAME (raw_example) really denotes the organisation identified by REF.",
 "Fill the column 'verdict (correct / wrong / unsure)' with exactly one of: correct, wrong, unsure. Optional free text in 'note'.",
 "Evidence, in order of usefulness:",
 " 1. registry_title_of_ref: the IATI Registry title of the organisation publishing under REF (empty if REF is not a publisher).",
 " 2. other_names_seen_with_ref: how other rows in the corpus call the organisation REF when both name and ref are given.",
 " 3. lookup_url: the official register for the ref prefix (ProPublica for US EINs, Charity Commission, Companies House, OSCR, KvK, IATI Registry).",
 " 4. reporter_example / reporter_example_title: who reported the rows; their activity pages on d-portal.org show the partner.",
 "Judge 'correct' also when the name is a sub-office, former name or spelling variant of the same organisation.",
 "Judge 'wrong' when REF is a different legal entity, a generic category (CRS channel code XX000), a placeholder, or another reporter's internal code reused for another organisation.",
 "suggested_verdict / auto_hint are heuristics only: please overrule them freely.",
 "When done, run: python3 r6_name_check_score.py  (prints the numbers for the two placeholders in paper/main.tex and patches them).",
]})
with pd.ExcelWriter("name_check_audit.xlsx", engine="openpyxl") as xw:
    out.to_excel(xw, index=False, sheet_name="sample")
    ws = xw.sheets["sample"]
    widths = {"A": 14, "B": 46, "C": 36, "D": 24, "E": 40, "F": 15, "G": 9, "H": 9, "I": 8, "J": 8, "K": 18, "L": 9,
              "M": 9, "N": 60, "O": 34, "P": 40, "Q": 70, "R": 16, "S": 26, "T": 40}
    for c, w in widths.items(): ws.column_dimensions[c].width = w
    ws.freeze_panes = "E2"
    howto.to_excel(xw, index=False, sheet_name="how_to")
    xw.sheets["how_to"].column_dimensions["A"].width = 160
out.to_csv("name_check_audit.tsv", sep="\t", index=False)
print("wrote name_check_audit.xlsx / .tsv")
