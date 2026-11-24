# Name-resolution audit: what the verdicts show (2026-11-18)

Verdicts: Paolo, via the claude.ai audit page (store exported to name_check_verdicts.json; raw
documents in audit_page/store/verdicts/). Scored by r7_name_check_score.py -> name_check_result.md.

## Headline numbers
- Random 100 pairs: 58 correct, 25 wrong, 17 unsure (pair-level error 25%, Wilson 95% CI 17.5-34.3%).
- Top 30 pairs by rows (57% of the 253,103 resolved rows): 25 correct, 4 wrong, 1 unsure.
  Wrong top pairs resolve 15,085 rows (10.5% of the top-30 rows).
- Row-weighted extrapolation (top-30 exact + random stratum rate 22.8% applied to the remaining
  108,890 rows): about 40,000 wrong rows, 16% of resolved rows (21% counting unsure as wrong).
  The random stratum has only 5,236 rows, dominated by three pairs, so this figure is rough.

## Error modes (by reference type, verdict counts correct/unsure/wrong, rows wrong)
- Generic CRS channel code or placeholder as target (1/2/15; 10,910 rows wrong): 'Correction' -> NOT
  AVAILABLE (8,611), Global Communities -> XM-DAC-21000 (1,823), INSO -> 20000 (363), ICJ, Progressio,
  IBLF, Civicus, PACT Institute, ORF, Conflict Dynamics, GURT, Sungi -> NOT REGISTERED, Plan -> NO
  IDENTIFIER, RSPB, CIPFA. Dictionary-wide: 243 of 2,174 pairs, 31,724 rows (12.5%) land on such codes;
  the graph also has 45 such pseudo-nodes from reporters' own refs (324 arcs, 1.1%; US$69.9 bn, 6.8%).
  => the single fix with the largest effect: treat ^(XM-DAC-)?\d{2}000$ and NOT AVAILABLE / NO
  IDENTIFIER / NOT REGISTERED as missing refs, blacklist 'correction'.
- UNICEF vendor codes XM-DAC-41122-VN-nnnnnn (1/5/5; 2,920 rows wrong): judged wrong/unsure on the
  reading VN = Vietnam. Checked in the raw data: 44,291 UNICEF rows carry such refs, 10,509 distinct
  codes, only 0.4% in Vietnam; each code goes with one name in the right country (CARE -> Cote
  d'Ivoire, Berytech -> Lebanon, Puntland WDA -> Somalia, Univ. of Zambia -> Zambia, NIMHANS ->
  India, ARSIS -> Albania, Health Office Al Jawf -> Yemen). VN = vendor number. These pairs identify
  the right organisation; the issue is only that the node is a reporter-specific duplicate of the
  organisation. Suggest: correct (or a separate class "correct, non-standard identifier").
- Name or acronym used as the ref by the reporter (8/3/2): LDMPCUL, CDFA, ANAPQUI ... judged correct,
  ADELPHI RESEARCH GGMBH and FUNDACAO MASC judged wrong, Springfield / ALLIMA CACAO / DPC unsure.
  Same phenomenon; needs one consistent rule (suggest correct, non-standard identifier).
- Bare numbers (1/0/3): 126799, 1013599 (reporter-internal numbers, wrong), 21032 = PSI in the CRS
  list and 477 corpus rows name it Population Services International -> judged wrong, probably a slip.
- Registered identifiers (72/7/3; 2,247 rows wrong): the only genuine misidentifications.
  International Medical Corps -> GB-COH-02651349 (DT Global UK, ex IMC Worldwide; 1,766 rows): a
  US NGO mapped to a UK consultancy sharing the acronym. UNECA -> XM-DAC-41305 (generic UN code;
  16 rows). Department of Works and Highways -> PG-COA-36910 (465 rows, no note; PG-COA is PNG's
  chart of accounts, the department is a PNG one: worth a second look).

## What to tell the reviewer
1. Pair-level accuracy 58-75% (random), but errors are concentrated in low-volume pairs and in two
   mechanical classes (category codes, placeholder strings) that are fixable upstream.
2. Genuine wrong-organisation mappings: 3 of 130 pairs, about 2,250 rows (0.9% of resolved rows).
3. We fixed the mechanical classes (if we do), re-ran the pipeline, and report before/after.
