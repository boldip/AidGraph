#!/usr/bin/env python3
"""Cycle/hierarchy invariants for the seven comparison networks (Table 10):

  - largest-SCC node share;
  - arcs on cycles: fraction of arcs whose endpoints lie in the same SCC
    (exactly the arcs participating in some directed cycle);
  - cyclic closure C3 = 3 * (#directed 3-cycles) / (#open directed 2-paths):
    the probability that a directed path u->v->w (u != w) is closed by the
    arc w->u into a 3-cycle; the directed-cycle analogue of transitivity;
  - trophic incoherence F0 (MacKay, Johnson & Nicosia, "How directed is a
    directed network?", R. Soc. Open Sci. 7:201138, 2020): trophic levels h
    minimise sum_(i->j) (h_j - h_i - 1)^2, F0 is the minimum divided by m;
    F0 = 0 is a perfect layered hierarchy, values near 1 are cycle-rich.
    Computed on the unweighted graph, consistent with the other columns.

Usage: python3 16_cycle_invariants.py
"""
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, diags
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import lsqr

NETWORKS = {
    "iati-k": "graph/arcs_weighted.tsv",
    "iati-cty": "comparison/aid_country.tsv",
    "ibank": "comparison/interbank.tsv",
    "refugee": "comparison/refugee.tsv",
    "air": "comparison/airline.tsv",
    "remit": "comparison/remit.tsv",
    "trade": "comparison/trade.tsv",
}


def invariants(path):
    a = pd.read_csv(path, sep="\t")
    src, dst = a.s.to_numpy(), a.d.to_numpy()
    n = int(max(src.max(), dst.max())) + 1
    m = len(src)
    A = coo_matrix((np.ones(m), (src, dst)), shape=(n, n)).tocsr()

    ncomp, comp = connected_components(A, directed=True, connection="strong")
    sizes = np.bincount(comp)
    scc_share = sizes.max() / n
    arcs_on_cycles = (comp[src] == comp[dst]).mean()

    # directed 3-cycles: sum over arcs (u,v) of |succ(v) cap pred(u)|, / 3
    succ = {}
    pred = {}
    for u, v in zip(src, dst):
        succ.setdefault(u, set()).add(v)
        pred.setdefault(u, set())
        pred.setdefault(v, set()).add(u)
        succ.setdefault(v, set())
    tri = sum(len(succ[v] & pred[u]) for u, v in zip(src, dst)) // 3
    # open directed 2-paths: sum_v din*dout minus the u->v->u cases,
    # whose count is the number of reciprocated arcs
    recip_arcs = sum(u in succ.get(v, ()) for u, v in zip(src, dst))
    din = np.asarray(A.sum(axis=0)).ravel()
    dout = np.asarray(A.sum(axis=1)).ravel()
    paths2 = int((din * dout).sum()) - recip_arcs
    c3 = 3 * tri / paths2 if paths2 else 0.0

    # trophic incoherence F0
    L = diags(din + dout) - A - A.T
    v = din - dout
    h = lsqr(L.tocsc(), v, atol=1e-12, btol=1e-12, iter_lim=20000)[0]
    F0 = float(((h[dst] - h[src] - 1) ** 2).sum() / m)

    return scc_share, arcs_on_cycles, tri, c3, F0


for name, path in NETWORKS.items():
    s, aoc, tri, c3, f0 = invariants(path)
    print(f"{name:9s} largest-SCC share {s:7.2%}  arcs on cycles {aoc:7.2%}  "
          f"3-cycles {tri:9,d}  C3 {c3:.4f}  F0 {f0:.3f}")
