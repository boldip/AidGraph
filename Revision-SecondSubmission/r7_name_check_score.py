#!/usr/bin/env python3
"""Score the hand audit (verdicts from name_check_verdicts.json, exported from the
claude.ai audit page, or from the workbook column) of the name-to-reference dictionary.

Reads the 'verdict (correct / wrong / unsure)' column of name_check_audit.xlsx
(sheet 'sample'), computes the numbers for the two [TO BE COMPLETED]
placeholders in paper/main.tex (Methods paragraph and response 3c), writes
name_check_result.md and, with --patch, replaces the placeholders.

  python3 r7_name_check_score.py          # report only
  python3 r7_name_check_score.py --patch  # also patch paper/main.tex
"""
import re, sys
import numpy as np, pandas as pd
from scipy.stats import beta

RESOLVED_TOTAL = 253_103   # ref-less receiver rows resolved by the dictionary (name_check_summary.md)
d = pd.read_excel("name_check_audit.xlsx", sheet_name="sample")
V = [c for c in d.columns if c.startswith("verdict")][0]
# verdicts exported from the audit artifact's store (name_check_verdicts.json: {"p<idx>": {"verdict":..., "note":...}})
# take precedence over the workbook column
import os, json
if os.path.exists("name_check_verdicts.json"):
    J = json.load(open("name_check_verdicts.json"))
    d[V] = d[V].astype(object); d["note"] = d["note"].astype(object)
    for k, body in J.items():
        i = int(k[1:])
        if body.get("verdict"): d.loc[i, V] = body["verdict"]
        if body.get("note"): d.loc[i, "note"] = body["note"]
    print(f"loaded {len(J)} verdicts from name_check_verdicts.json")
v = d[V].astype(str).str.strip().str.lower().replace({"nan": "", "none": ""})
ok = v.isin(["correct", "wrong", "unsure"])
if not ok.all():
    bad = d.loc[~ok, ["stratum", "raw_example", "ref", V]]
    sys.exit(f"{len(bad)} rows without a valid verdict (correct / wrong / unsure):\n{bad.to_string()}")
d["v"] = v

def wilson(k, n, z=1.96):
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h

rand = d[d.in_random_sample]; top = d[d.stratum == "top 30 by rows"]
assert len(rand) == 100 and len(top) == 30
cr, wr, ur = (rand.v == "correct").sum(), (rand.v == "wrong").sum(), (rand.v == "unsure").sum()
ct, wt, ut = (top.v == "correct").sum(), (top.v == "wrong").sum(), (top.v == "unsure").sum()
wrong_rows_top = int(top.loc[top.v == "wrong", "rows"].sum())
wrong_rows_all = int(d.loc[d.v == "wrong", "rows"].sum())
lo, hi = wilson(wr, 100)
# Clopper-Pearson for the pair-level error rate as well
cp = (beta.ppf(0.025, wr, 100 - wr + 1) if wr else 0.0, beta.ppf(0.975, wr + 1, 100 - wr))
top_share = top.rows.sum() / RESOLVED_TOTAL
notes = d.loc[d.v == "wrong", "note"].dropna().astype(str).str.strip()
notes = notes[notes != ""]

lines = [
 "# Name-resolution audit: result", "",
 f"- random 100 pairs: {cr} correct, {wr} wrong, {ur} unsure; pair-level error rate {wr/100:.0%} (Wilson 95% CI {lo:.1%} to {hi:.1%}; Clopper-Pearson {cp[0]:.1%} to {cp[1]:.1%})",
 f"- top 30 pairs by rows ({top_share:.1%} of resolved rows): {ct} correct, {wt} wrong, {ut} unsure; wrong pairs resolve {wrong_rows_top:,} rows ({wrong_rows_top/RESOLVED_TOTAL:.1%} of the resolved total)",
 f"- all wrong pairs in the sample: {wrong_rows_all:,} rows ({wrong_rows_all/RESOLVED_TOTAL:.1%} of the resolved total)", "",
 "Wrong pairs:", ]
for r in d[d.v == "wrong"].sort_values("rows", ascending=False).itertuples():
    lines.append(f"- [{r.stratum}] '{r.raw_example}' -> {r.ref} ({r.registry_title_of_ref if isinstance(r.registry_title_of_ref, str) else 'no registry title'}), {r.rows:,} rows" + (f": {r.note}" if isinstance(r.note, str) and r.note.strip() else ""))
if (d.v == "unsure").any():
    lines += ["", "Unsure pairs:"] + [f"- [{r.stratum}] '{r.raw_example}' -> {r.ref}, {r.rows:,} rows" for r in d[d.v == "unsure"].itertuples()]

uns_r = f" and {ur} could not be settled" if ur else ""
uns_t = f" ({ut} unsettled)" if ut else ""
methods = (f"{cr} of the 100 random pairs were correct, {wr} were wrong{uns_r}; {ct} of the 30 high-volume pairs were correct{uns_t}. "
           f"The wrong pairs in the sample resolve {wrong_rows_all:,} rows, {wrong_rows_all/RESOLVED_TOTAL*100:.1f}\\% of the resolved total"
           + (f"; the errors were {'; '.join(notes.unique()[:4])}" if len(notes) else "") + ".")
response = (f"{cr} of the 100 random pairs ({wr} wrong{uns_r}) and {ct} of the 30 high-volume pairs{uns_t} were confirmed; "
            f"the wrong pairs resolve {wrong_rows_all:,} rows ({wrong_rows_all/RESOLVED_TOTAL*100:.1f}\\% of the resolved total). "
            f"The pair-level error rate is therefore about {wr}\\% (95\\% CI {lo*100:.0f} to {hi*100:.0f}\\%), concentrated in low-volume pairs.")
lines += ["", "Proposed Methods sentence:", "", methods, "", "Proposed response sentence (3c):", "", response]
open("name_check_result.md", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))

if "--patch" in sys.argv:
    tex = open("paper/main.tex").read()
    n = 0
    tex, k = re.subn(r"\[TO BE COMPLETED: \$x\$ of the 100 random pairs.*?\]", methods, tex, flags=re.S); n += k
    tex, k = re.subn(r"\[TO BE COMPLETED with the audit result; the sentence in Methods has a matching placeholder\.\]", response, tex); n += k
    assert n == 2, f"replaced {n} placeholders, expected 2"
    open("paper/main.tex", "w").write(tex); print("\npatched paper/main.tex (2 placeholders); recompile with latexmk -pdf main.tex in paper/")
