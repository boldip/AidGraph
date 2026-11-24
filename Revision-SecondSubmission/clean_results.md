# IATI-K rebuilt without generic category codes and placeholder references

Build log:

- total rows: 10,890,453
- disbursement rows after dedup and secondary-reporter removal: 3,643,369
- category-like codes kept because an organisation publishes under them: ['44000', 'XM-DAC-43000']
- rows whose receiver ref is a generic category code or placeholder string: 218,789 (provider: 0); distinct such receiver refs: 43
- receiver names newly blacklisted as category labels: 75,066 rows, e.g. {'enterprise - non united states other': 34851, 'correction': 22012, 'international ngo': 5404, 'enterprise - united states other': 2636, 'ngo - non united states other': 2607, 'national ngo': 2228, 'developing country-based ngo': 1549, 'university college research other': 1231}
- name->ref dictionary entries: 12,674 (published build: 13,875)
- ref-less receivers resolved by name dictionary: 275,378 rows (published build: 269,090)
- distinct (name, ref) pairs used: 2,316; resolving onto generic codes: 2
- rows with both endpoints: 1,118,457 (published: 1,330,963)
- self-loop rows dropped: 279,898; rows used for arcs: 838,559 (published: 1,051,065)
- total net disbursement value: 1,017.82 B USD (published: 1,030.38)
- n = 22,771 nodes (published 22,773); m = 28,825 arcs (published 28,708)
- audit sample: 20 of 128 pairs no longer produced by the dictionary: 15 wrong, 2 unsure, 3 correct (10,910 of the 13,177 rows judged wrong)
- remaining sample: random 84 pairs: 72 correct, 4 wrong, 7 unsure; top-30: 24 / 1 / 0

## Invariants

|                      |   IATI-K (published) |    IATI-K clean |
|:---------------------|---------------------:|----------------:|
| n                    |      22773           | 22771           |
| m                    |      28708           | 28825           |
| funders              |        852           |   848           |
| receivers            |      22378           | 22384           |
| in_degree_1_share    |          0.909956    |     0.906362    |
| giant_wcc            |      22461           | 22467           |
| giant_wcc_share      |          0.9863      |     0.98665     |
| largest_scc          |        197           |   200           |
| cyclic_arc_share     |          0.0422879   |     0.0437814   |
| reciprocity          |          0.00849937  |     0.00846487  |
| reachable_pairs      |          5.74455e+06 |     5.81558e+06 |
| reachable_pair_share |          0.0110773   |     0.0112163   |
| avg_distance         |          5.9982      |     5.4881      |
| eff_diameter_90      |          8           |     7           |
| max_distance         |         13           |    13           |
| share_dist_le2       |          0.0203583   |     0.0221818   |
| share_dist_5to7      |          0.721173    |     0.685619    |

## Distance distribution (share of reachable pairs)

|   distance |       pairs_full |      pairs_clean |   share_full |   share_clean |
|-----------:|-----------------:|-----------------:|-------------:|--------------:|
|          1 |  28708           |  28825           |  0.00499743  |   0.00495651  |
|          2 |  88241           | 100175           |  0.0153608   |   0.0172253   |
|          3 | 212334           | 282852           |  0.0369627   |   0.0486369   |
|          4 | 526584           | 933641           |  0.0916667   |   0.160541    |
|          5 |      1.05935e+06 |      1.7058e+06  |  0.18441     |   0.293315    |
|          6 |      1.71383e+06 |      1.51466e+06 |  0.298341    |   0.260449    |
|          7 |      1.36963e+06 | 766818           |  0.238423    |   0.131856    |
|          8 | 519249           | 319153           |  0.0903899   |   0.054879    |
|          9 | 138798           |  97624           |  0.0241617   |   0.0167866   |
|         10 |  43591           |  43524           |  0.00758824  |   0.00748403  |
|         11 |  29297           |  18422           |  0.00509997  |   0.0031677   |
|         12 |  14195           |   3356           |  0.00247104  |   0.00057707  |
|         13 |    736           |    735           |  0.000128121 |   0.000126385 |

## Funder removal (clean graph)

| k | by USD | by out-degree | by harmonic | random |
|---|---|---|---|---|
| 1 | 0.987 / 100% | 0.512 / 48% | 0.512 / 48% | 0.986 / 100% |
| 3 | 0.982 / 94% | 0.409 / 27% | 0.409 / 27% | 0.985 / 99% |
| 10 | 0.896 / 14% | 0.271 / 14% | 0.379 / 14% | 0.982 / 98% |
| 50 | 0.475 / 9% | 0.110 / 3% | 0.314 / 5% | 0.941 / 85% |

Cells: giant-component share / share of reachable pairs still open.

## H1 ranking on the clean graph

282 funders pass the activity filter (285 published). Over the 280 common funders, Spearman rho(z_new, z_old) = 0.979, Kendall tau = 0.916; top-50 overlap 40/50.

Top 20 (new rank, old rank):

- 1 (6) CARE International UK: z 2.66 (was 2.12), out-degree 35, US$549.6m
- 2 (8) MSI Reproductive Choices: z 2.58 (was 2.09), out-degree 23, US$105.5m
- 3 (13) Gavi, the vaccine alliance: z 2.55 (was 1.83), out-degree 59, US$29,248.0m
- 4 (2) Gates Foundation: z 2.50 (was 2.37), out-degree 240, US$26,785.7m
- 5 (1) ODI Global: z 2.50 (was 2.37), out-degree 5, US$9.0m
- 6 (3) Mott MacDonald Limited: z 2.41 (was 2.26), out-degree 5, US$64.8m
- 7 (5) Aga Khan Foundation (United Kingdom): z 2.28 (was 2.15), out-degree 6, US$126.0m
- 8 (12) United States Department of Defense: z 2.24 (was 1.84), out-degree 7, US$89,283.5m
- 9 (4) The William and Flora Hewlett Foundation: z 2.09 (was 2.22), out-degree 393, US$1,880.7m
- 10 (31) UK - Department of Health and Social Care (DHSC): z 2.08 (was 1.40), out-degree 108, US$3,412.5m
- 11 (7) London School of Hygiene and Tropical Medicine: z 2.01 (was 2.10), out-degree 7, US$22.1m
- 12 (15) United States Department of Commerce: z 1.90 (was 1.69), out-degree 11, US$64.3m
- 13 (19) The University of Oxford: z 1.86 (was 1.57), out-degree 5, US$63.0m
- 15 (10) ActionAid Rwanda: z 1.80 (was 1.88), out-degree 5, US$3.5m
- 16 (9) XM-OCHA-CBPF-TCD90: z 1.78 (was 1.89), out-degree 5, US$5.7m
- 17 (94) UK - Foreign, Commonwealth and Development Office: z 1.77 (was 0.87), out-degree 1221, US$162,694.4m
- 18 (16) Inter-American Foundation: z 1.76 (was 1.61), out-degree 15, US$586.7m
- 19 (18) United States Department of the Treasury: z 1.76 (was 1.60), out-degree 19, US$30,746.3m
- 20 (14) The Hunger Project Netherlands: z 1.71 (was 1.76), out-degree 5, US$53.2m
- 21 (25) World Vision UK: z 1.63 (was 1.49), out-degree 14, US$285.0m

Largest rank changes (|new - old| >= 20):

- Global Innovation Fund: 216 -> 62 (z -0.76 -> 1.22)
- DE-CR-7745: 236 -> 97 (z -0.97 -> 0.94)
- UK - Foreign, Commonwealth and Development Office: 94 -> 17 (z 0.87 -> 1.77)
- United States Department of State: 85 -> 27 (z 0.95 -> 1.55)
- Denmark - Ministry of Foreign Affairs, Danida: 88 -> 49 (z 0.94 -> 1.29)
- The International Rescue Committee: 119 -> 91 (z 0.71 -> 0.99)
- Canada - International Development Research Centre/Centre de recherches pour le développement international: 137 -> 110 (z 0.55 -> 0.86)
- HelpAge International: 209 -> 184 (z -0.74 -> -0.68)
- International Labour Organization (ILO): 113 -> 88 (z 0.76 -> 1.03)
- CREA: 215 -> 191 (z -0.76 -> -0.73)
- KPMG Advisory Limited (Tanzania): 65 -> 42 (z 1.12 -> 1.36)
- PwC: 112 -> 89 (z 0.76 -> 1.02)
- UK - Department of Health and Social Care (DHSC): 31 -> 10 (z 1.40 -> 2.08)
- Norwegian People's Aid: 206 -> 186 (z -0.73 -> -0.72)
- Adam Smith International: 39 -> 59 (z 1.30 -> 1.23)
- Terre des Hommes Netherlands: 36 -> 58 (z 1.34 -> 1.23)
- Asian Development Bank: 182 -> 204 (z -0.54 -> -0.77)
- AICS - Agenzia Italiana per la Cooperazione allo Sviluppo / Italian Agency for Cooperation and Development: 183 -> 206 (z -0.57 -> -0.79)
- Center for Church-Based Development: 204 -> 229 (z -0.73 -> -0.98)
- Afr.DF/African Development Fund: 187 -> 213 (z -0.66 -> -0.83)
- Fair Wear Foundation: 56 -> 87 (z 1.16 -> 1.05)
- Education Cannot Wait: 97 -> 133 (z 0.83 -> 0.69)
- reference: United States Agency for International Development (USAID): rank 156 (was 156), z 0.37 (was 0.31)
- reference: UK - Foreign, Commonwealth and Development Office: rank 17 (was 94), z 1.77 (was 0.87)
- reference: United States Department of State: rank 27 (was 85), z 1.55 (was 0.95)
- reference: Sweden, through Swedish International Development Cooperation Agency (Sida): rank 141 (was 123), z 0.57 (was 0.69)
- reference: Denmark - Ministry of Foreign Affairs, Danida: rank 49 (was 88), z 1.29 (was 0.94)
- reference: GlobalGiving.org: rank 282 (was 285), z -13.67 (was -12.84)
