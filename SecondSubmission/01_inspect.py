#!/usr/bin/env python3
"""Step 1-3a: inspect IATI_All_Transactions.parquet and profile identifier coverage.

Reads the parquet metadata and data, reports:
  - schema and row count
  - distribution of transaction_transaction_type_code
  - type-3 row count, raw and after full-row deduplication
    (expected per Elaine: 3,680,429 raw; 2,583,194 dedup)
  - provider/receiver ref vs name coverage on type-3 rows,
    to inform the node-identity decision.

Usage: python3 01_inspect.py IATI_All_Transactions.parquet
"""
import sys

import pandas as pd
import pyarrow.parquet as pq

TYPE_COL_CANDIDATES = [
    "transaction_transaction_type_code",
    "transaction_type_code",
    "transaction_type",
]


def find_col(cols, *needles, forbid=()):
    """Return columns whose lowercased name contains all needles and no forbidden token."""
    out = []
    for c in cols:
        lc = c.lower()
        if all(n in lc for n in needles) and not any(f in lc for f in forbid):
            out.append(c)
    return out


def main(path):
    pf = pq.ParquetFile(path)
    print(f"== File: {path}")
    print(f"rows: {pf.metadata.num_rows:,}   row groups: {pf.metadata.num_row_groups}")
    print("\n== Schema ==")
    for f in pf.schema_arrow:
        print(f"  {f.name}: {f.type}")

    cols = [f.name for f in pf.schema_arrow]
    type_col = next((c for c in TYPE_COL_CANDIDATES if c in cols), None)
    if type_col is None:
        cands = find_col(cols, "type")
        print(f"\n!! No expected transaction-type column found; candidates: {cands}")
        return

    # Columns of interest for the profile
    prov_ref = find_col(cols, "provider", "ref")
    prov_name = find_col(cols, "provider", "narrative") or find_col(cols, "provider", "name")
    recv_ref = find_col(cols, "receiver", "ref")
    recv_name = find_col(cols, "receiver", "narrative") or find_col(cols, "receiver", "name")
    hum = find_col(cols, "humanitarian")
    print(f"\nidentifier columns -> provider ref: {prov_ref}, provider name: {prov_name}")
    print(f"                      receiver ref: {recv_ref}, receiver name: {recv_name}")
    print(f"humanitarian flag columns: {hum}")

    df_type = pd.read_parquet(path, columns=[type_col])
    print(f"\n== {type_col} distribution ==")
    print(df_type[type_col].value_counts(dropna=False).to_string())

    # Full-row dedup check on type-3 (read everything; ~3.7M rows is fine in RAM)
    df = pd.read_parquet(path)
    t3 = df[df[type_col].astype(str).str.strip() == "3"]
    print(f"\n== Type-3 (disbursements) ==")
    print(f"raw rows:          {len(t3):,}   (Elaine: 3,680,429)")
    ded = t3.drop_duplicates()
    print(f"after full dedup:  {len(ded):,}   (Elaine: 2,583,194)")

    print("\n== Identifier coverage on deduplicated type-3 rows ==")
    n = len(ded)
    for label, refs, names in (("provider", prov_ref, prov_name),
                               ("receiver", recv_ref, recv_name)):
        rc = refs[0] if refs else None
        nc = names[0] if names else None
        has_ref = ded[rc].notna() & (ded[rc].astype(str).str.strip() != "") if rc else pd.Series(False, index=ded.index)
        has_name = ded[nc].notna() & (ded[nc].astype(str).str.strip() != "") if nc else pd.Series(False, index=ded.index)
        print(f"  {label}: ref {has_ref.sum():,} ({has_ref.mean():.1%})  "
              f"name {has_name.sum():,} ({has_name.mean():.1%})  "
              f"neither {(~has_ref & ~has_name).sum():,} ({(~has_ref & ~has_name).mean():.1%})")
        if rc and nc:
            both = ded[has_ref & has_name]
            mult = both.groupby(rc)[nc].nunique()
            print(f"    refs with >1 distinct name: {(mult > 1).sum():,} of {len(mult):,} refs "
                  f"(max {mult.max() if len(mult) else 0} names per ref)")
            distinct_refs = ded.loc[has_ref, rc].str.strip().nunique()
            distinct_names = ded.loc[has_name, nc].str.strip().nunique()
            print(f"    distinct refs: {distinct_refs:,}   distinct names: {distinct_names:,}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "IATI_All_Transactions.parquet")
