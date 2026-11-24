# Backboning robustness (IATI-K)

Full graph: n = 22,771 nodes with arcs = 22,771, m = 28,825.

## What survives each backbone

| backbone              |     n |     m |   arc_share |   usd_share |   giant_wcc_share |   reachable_pairs |   avg_distance |   in_degree_1_share |   gg_arcs_kept |   funders_filtered_kept |   rho_h_vs_full |   top50_h_overlap |
|:----------------------|------:|------:|------------:|------------:|------------------:|------------------:|---------------:|--------------------:|---------------:|------------------------:|----------------:|------------------:|
| full                  | 22771 | 28825 |       1.000 |       1.000 |             0.987 |           5815581 |          5.488 |               0.906 |          10818 |                     282 |           1.000 |                50 |
| disparity_usd_a0.05   |  2162 |  2510 |       0.087 |       0.779 |             0.667 |              8713 |          2.815 |               0.887 |            554 |                     218 |           0.612 |                30 |
| disparity_usd_a0.1    |  2735 |  3279 |       0.114 |       0.821 |             0.938 |             15563 |          3.159 |               0.878 |            707 |                     247 |           0.647 |                29 |
| disparity_usd_a0.2    |  3695 |  4589 |       0.159 |       0.874 |             0.934 |             26550 |          3.333 |               0.870 |            998 |                     266 |           0.652 |                31 |
| noisecorr_usd_d1.28   | 22679 | 27457 |       0.953 |       0.957 |             0.987 |           4819617 |          6.052 |               0.913 |          10804 |                     282 |           0.899 |                36 |
| noisecorr_usd_d1.64   | 22679 | 27457 |       0.953 |       0.957 |             0.987 |           4819617 |          6.052 |               0.913 |          10804 |                     282 |           0.899 |                36 |
| noisecorr_usd_d2.33   | 22679 | 27457 |       0.953 |       0.957 |             0.987 |           4819617 |          6.052 |               0.913 |          10804 |                     282 |           0.899 |                36 |
| disparity_count_a0.05 |  1651 |  1912 |       0.066 |       0.600 |             0.579 |              6077 |          2.576 |               0.893 |            503 |                     167 |           0.475 |                33 |
| disparity_count_a0.1  |  2363 |  2784 |       0.097 |       0.656 |             0.575 |             12004 |          2.891 |               0.886 |            682 |                     209 |           0.562 |                32 |
| disparity_count_a0.2  |  4107 |  4946 |       0.172 |       0.727 |             0.588 |             32310 |          3.654 |               0.888 |           1445 |                     253 |           0.668 |                34 |
| noisecorr_count_d1.28 | 22771 | 27526 |       0.955 |       0.924 |             0.987 |           5352682 |          5.654 |               0.911 |          10818 |                     282 |           0.958 |                41 |
| noisecorr_count_d1.64 | 22771 | 27457 |       0.953 |       0.922 |             0.987 |           5352413 |          5.659 |               0.911 |          10818 |                     282 |           0.958 |                41 |
| noisecorr_count_d2.33 | 22771 | 27337 |       0.948 |       0.920 |             0.987 |           5331373 |          5.670 |               0.912 |          10818 |                     282 |           0.954 |                39 |

rho/tau: Spearman/Kendall between harmonic centrality on the backbone and on the full graph, over the activity-filtered funders present in the backbone; top50 overlap: of the top 50 by harmonic centrality among those funders.

## Null-model z on disparity_usd_a0.05

59 funders pass the activity filter on this backbone (282 on the full graph); over the 59 in common: Spearman rho(z) = 0.501, Kendall tau = 0.376; top-50 overlap with the published top 50: 8.

Top 15 (backbone rank, published rank):

- 1 (49) Denmark - Ministry of Foreign Affairs, Danida: z 3.43 (was 1.29), out-degree 79
- 2 (159) Netherlands - Ministry of Foreign Affairs: z 2.96 (was 0.34), out-degree 65
- 3 (17) UK - Foreign, Commonwealth and Development Office: z 2.05 (was 1.77), out-degree 188
- 4 (172) Belgian Development Cooperation: z 0.89 (was 0.15), out-degree 18
- 5 (228) Canada - Global Affairs Canada | Affaires mondiales Canada: z 0.68 (was -0.95), out-degree 47
- 6 (27) United States Department of State: z 0.46 (was 1.55), out-degree 53
- 7 (147) United Nations Children's Fund (UNICEF): z 0.31 (was 0.49), out-degree 5
- 8 (61) Stichting Beheer Subsidiegelden DRA: z 0.25 (was 1.22), out-degree 7
- 9 (138) UNITAID: z 0.24 (was 0.63), out-degree 6
- 10 (88) International Labour Organization (ILO): z 0.23 (was 1.03), out-degree 5
- 11 (141) Sweden, through Swedish International Development Cooperation Agency (Sida): z 0.21 (was 0.57), out-degree 70
- 12 (167) Ireland - Department of Foreign Affairs: z 0.20 (was 0.21), out-degree 99
- 13 (64) European Commission - Humanitarian Aid & Civil Protection: z 0.14 (was 1.20), out-degree 9
- 14 (137) XM-OCHA-CBPF-AFG23: z 0.13 (was 0.64), out-degree 5
- 15 (135) UN Pooled Funds: z -0.00 (was 0.68), out-degree 7
- published top 10 now at: CARE International UK dropped, MSI Reproductive Choices dropped, Gavi, the vaccine alliance dropped, Gates Foundation 50, ODI Global dropped, Mott MacDonald Limited dropped, Aga Khan Foundation (United Kingdom) dropped, United States Department of Defense dropped, The William and Flora Hewlett Foundation 44, UK - Department of Health and Social Care (DHSC) 53

## Null-model z on noisecorr_usd_d1.64

275 funders pass the activity filter on this backbone (282 on the full graph); over the 275 in common: Spearman rho(z) = 0.911, Kendall tau = 0.798; top-50 overlap with the published top 50: 33.

Top 15 (backbone rank, published rank):

- 1 (7) Aga Khan Foundation (United Kingdom): z 3.25 (was 2.28), out-degree 6
- 2 (16) XM-OCHA-CBPF-TCD90: z 2.89 (was 1.78), out-degree 5
- 3 (20) The Hunger Project Netherlands: z 2.71 (was 1.71), out-degree 5
- 4 (13) The University of Oxford: z 2.62 (was 1.86), out-degree 5
- 5 (15) ActionAid Rwanda: z 2.62 (was 1.80), out-degree 5
- 6 (14) Plan International UK: z 2.60 (was 1.81), out-degree 5
- 7 (1) CARE International UK: z 2.52 (was 2.66), out-degree 27
- 8 (26) War Child Alliance Foundation: z 2.50 (was 1.55), out-degree 7
- 9 (41) Mensen met een Missie: z 2.47 (was 1.37), out-degree 6
- 10 (22) SNV Netherlands Development Organisation: z 2.42 (was 1.61), out-degree 7
- 11 (23) International Fertilizer Development Center: z 2.37 (was 1.58), out-degree 5
- 12 (3) Gavi, the vaccine alliance: z 2.36 (was 2.55), out-degree 42
- 13 (25) XM-OCHA-CBPF-NER84: z 2.32 (was 1.57), out-degree 7
- 14 (48) CARE Nederland: z 2.28 (was 1.30), out-degree 9
- 15 (4) Gates Foundation: z 2.26 (was 2.50), out-degree 198
- published top 10 now at: CARE International UK 7, MSI Reproductive Choices 31, Gavi, the vaccine alliance 12, Gates Foundation 15, ODI Global dropped, Mott MacDonald Limited dropped, Aga Khan Foundation (United Kingdom) 1, United States Department of Defense 16, The William and Flora Hewlett Foundation 63, UK - Department of Health and Social Care (DHSC) 154
