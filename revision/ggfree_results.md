# IATI-K without GlobalGiving

GlobalGiving (US-EIN-300108263): out-degree 10,818 = 47.5% of the 22,771 organisations; in-degree 3; 10,818 of its recipients (100.0%) have no other identified funder.

Reachable ordered pairs: 5,815,581 -> 2,797,081 (3,018,500 = 51.9% of reachable pairs involve GlobalGiving as source, target or intermediary).
Distance-2 pairs: 100,175 -> 67,714 (32.4% of the distance-2 peak is GlobalGiving).

## Invariants

|                      |          IATI-K |   IATI-K without GlobalGiving |
|:---------------------|----------------:|------------------------------:|
| n                    | 22771           |               11952           |
| m                    | 28825           |               18004           |
| funders              |   848           |                 847           |
| receivers            | 22384           |               11565           |
| in_degree_1_share    |     0.906362    |                   0.81885     |
| giant_wcc            | 22467           |               11648           |
| giant_wcc_share      |     0.98665     |                   0.974565    |
| largest_scc          |   200           |                 200           |
| cyclic_arc_share     |     0.0437814   |                   0.0700955   |
| reciprocity          |     0.00846487  |                   0.0135525   |
| reachable_pairs      |     5.81558e+06 |                   2.79708e+06 |
| reachable_pair_share |     0.0112163   |                   0.0195821   |
| avg_distance         |     5.4881      |                   5.60107     |
| eff_diameter_90      |     7           |                   8           |
| max_distance         |    13           |                  13           |
| share_dist_le2       |     0.0221818   |                   0.0306455   |
| share_dist_5to7      |     0.685619    |                   0.601672    |

## Funder removal (GG-free graph, shares relative to its own 11,952 nodes)

| k | by USD | by out-degree | by harmonic | random |
|---|---|---|---|---|
| 1 | 0.974 / 100% | 0.835 / 66% | 0.835 / 66% | 0.974 / 100% |
| 3 | 0.965 / 89% | 0.700 / 57% | 0.757 / 32% | 0.971 / 99% |
| 10 | 0.801 / 27% | 0.493 / 28% | 0.687 / 27% | 0.966 / 96% |
| 50 | 0.402 / 18% | 0.205 / 7% | 0.508 / 9% | 0.927 / 84% |

Cells: giant-component share / share of the graph's own reachable pairs still open.

- first removed by usd: United States Agency for International Development (USAID), then United States Department of State, Asian Development Bank
- first removed by degree: Ireland - Department of Foreign Affairs, then UK - Foreign, Commonwealth and Development Office, International Development Association
- first removed by harmonic: Ireland - Department of Foreign Affairs, then UK - Foreign, Commonwealth and Development Office, Denmark - Ministry of Foreign Affairs, Danida

## H1 ranking on the GG-free graph

281 funders pass the activity filter (282 before; GlobalGiving itself is gone). Over the 281 common funders, Spearman rho(z_new, z_old) = 0.950, Kendall tau = 0.864; top-50 overlap 40/50.

Top 20 (new rank, old rank):

- 1 (49) Denmark - Ministry of Foreign Affairs, Danida: z 3.27 (was 1.29), out-degree 567, US$112,467.7m
- 2 (3) Gavi, the vaccine alliance: z 2.97 (was 2.55), out-degree 59, US$29,248.0m
- 3 (1) CARE International UK: z 2.79 (was 2.66), out-degree 35, US$549.6m
- 4 (2) MSI Reproductive Choices: z 2.68 (was 2.58), out-degree 23, US$105.5m
- 5 (27) United States Department of State: z 2.22 (was 1.55), out-degree 298, US$213,305.1m
- 6 (8) United States Department of Defense: z 2.20 (was 2.24), out-degree 7, US$89,283.5m
- 7 (10) UK - Department of Health and Social Care (DHSC): z 2.18 (was 2.08), out-degree 108, US$3,412.5m
- 8 (6) Mott MacDonald Limited: z 2.05 (was 2.41), out-degree 5, US$64.8m
- 9 (5) ODI Global: z 1.99 (was 2.50), out-degree 5, US$9.0m
- 10 (46) United States Health and Human Services: z 1.95 (was 1.30), out-degree 62, US$33,417.7m
- 11 (19) United States Department of the Treasury: z 1.92 (was 1.76), out-degree 19, US$30,746.3m
- 12 (66) Save the Children Netherlands: z 1.82 (was 1.17), out-degree 31, US$160.0m
- 13 (7) Aga Khan Foundation (United Kingdom): z 1.81 (was 2.28), out-degree 6, US$126.0m
- 14 (18) Inter-American Foundation: z 1.80 (was 1.76), out-degree 15, US$586.7m
- 15 (20) The Hunger Project Netherlands: z 1.80 (was 1.71), out-degree 5, US$53.2m
- 16 (11) London School of Hygiene and Tropical Medicine: z 1.80 (was 2.01), out-degree 7, US$22.1m
- 17 (12) United States Department of Commerce: z 1.78 (was 1.90), out-degree 11, US$64.3m
- 18 (16) XM-OCHA-CBPF-TCD90: z 1.69 (was 1.78), out-degree 5, US$5.7m
- 19 (24) United States Trade and Development Agency: z 1.65 (was 1.58), out-degree 20, US$478.2m
- 20 (141) Sweden, through Swedish International Development Cooperation Agency (Sida): z 1.56 (was 0.57), out-degree 333, US$99,858.5m
- reference: United States Agency for International Development (USAID): rank 104 (was 156), z 0.84 (was 0.37)
- reference: UK - Foreign, Commonwealth and Development Office: rank 25 (was 17), z 1.49 (was 1.77)
- reference: Denmark - Ministry of Foreign Affairs, Danida: rank 1 (was 49), z 3.27 (was 1.29)
