# Receiver-name resolution: check sample

- dictionary entries: 13,718
- ref-less named receiver rows resolved: 253,103, distinct (name, ref) pairs: 2,174
- pairs from publisher titles: 316; from co-occurrence: 1,858
- top 30 pairs account for 57.0% of resolved rows; top 100 for 76.7%
- resolved rows where the target ref is the reporting organisation itself (internal transfer, dropped as self-loop later): 19,400

Sample: 100 pairs uniformly at random (seed 2026) + the 30 pairs resolving the most rows, in name_check_sample.xlsx with an empty verdict column.



Generic targets (r6_name_check_enrich.py):
- resolved rows whose target ref is a generic CRS channel code or placeholder: 31,724 of 253,103 (12.53%), in 243 of 2,174 pairs
- by target: NOT AVAILABLE 8,611 rows/1 pairs; XM-DAC-21000 5,706 rows/27 pairs; 22000 2,751 rows/36 pairs; XM-DAC-63000 2,500 rows/1 pairs; 20000 2,098 rows/21 pairs; 23000 1,981 rows/16 pairs; 12000 1,393 rows/16 pairs; XM-DAC-22000 1,144 rows/14 pairs; XM-DAC-90000 1,029 rows/7 pairs; XM-DAC-12000 895 rows/5 pairs; XM-DAC-61000 785 rows/1 pairs; XM-DAC-51000 751 rows/18 pairs; 44000 709 rows/1 pairs; XM-DAC-23000 393 rows/22 pairs; 21000 341 rows/10 pairs; NOT REGISTERED 220 rows/16 pairs; 11000 145 rows/7 pairs; 31000 75 rows/2 pairs; XM-DAC-13000 74 rows/1 pairs; 41000 28 rows/1 pairs; XM-DAC-47000 25 rows/1 pairs; NO IDENTIFIER 24 rows/14 pairs; 13000 16 rows/2 pairs; XM-DAC-45000 15 rows/1 pairs; XM-DAC-44000 14 rows/1 pairs; 32000 1 rows/1 pairs
