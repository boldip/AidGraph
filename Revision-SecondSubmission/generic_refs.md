# Generic receiver references in the graph (found during the name audit, 2026-11-17)

Reporters sometimes give as receiver-org *reference* an OECD CRS channel
category code (21000 "International NGO", 22000 "Donor country-based NGO",
61000 "Private sector in provider country", 12000 "Recipient government",
44000 "World Bank group", ...), with or without the XM-DAC- prefix, or a
placeholder string (NOT AVAILABLE, NO IDENTIFIER, NOT REGISTERED). Our
PLACEHOLDER list in 02_build_graph.py does not catch these, so they become
nodes.

In the published graph (graph/nodes.tsv, graph/arcs_weighted.tsv):

- 45 such pseudo-nodes, all pure receivers (never a source)
- 324 arcs point to them: 1.13% of the 28,708 arcs
- US$69.9 bn flows into them: 6.78% of the US$1,030 bn on the arcs
- largest: US State -> XM-DAC-61000 ($9.9 bn, 43,380 transactions);
  FCDO -> 22000 ($6.4 bn); UNHCR -> XM-DAC-21000 ($5.9 bn); FCDO -> 12000 ($5.9 bn);
  Sida -> XM-DAC-22000 ($4.7 bn); Netherlands MFA -> 44000 ($3.5 bn)
- by source: FCDO $20.5 bn, US State $16.4 bn, Sida $13.8 bn, UNHCR $5.9 bn, Netherlands $5.4 bn

The name-to-reference dictionary also resolves names onto these codes:
31,724 of 253,103 resolved rows (12.5%), in 243 of 2,174 pairs, mostly
because the *name* is itself a category label ("INTERNATIONAL NGO",
"Enterprise - Non United States Other", "Correction") that co-occurs with the
code; but some real organisations are mapped to a code as well (e.g. Global
Communities, Forest Peoples Programme, PACT Institute -> XM-DAC-21000).

Impact assessment: by arc count the pseudo-nodes are negligible (1.1%);
by USD they are not (6.8%), so USD-weighted quantities (identified share
49.6%/44%, USD percolation order, the scale axis of Fig. 3) would move
slightly if they were dropped. Degree- and distance-based results cannot
change by more than ~1% of arcs, and the pseudo-nodes are sinks, so distances
through them do not exist. Recommended fix for the revision: add
`^(XM-DAC-)?\d{2}000$` and the three placeholder strings to PLACEHOLDER,
rebuild, and report the before/after invariants in the robustness section
(or state the 1.1%/6.8% figures and keep the graph as is).
