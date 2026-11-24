#!/bin/bash
# Steps 4-6: BVGraph build, exact neighbourhood function, HyperBall, SCC.
#
# Input : graph/arclist.txt  — one arc per line "src<TAB>dst", integer ids from 0,
#                              sorted numerically by src then dst, no duplicates.
# Output: graph/aid* BVGraph files, graph/aid-t* transpose,
#         graph/nf-exact.txt (exact neighbourhood function),
#         graph/nf-hyperball.txt (HyperBall estimate, log2m=12),
#         graph/scc-sizes.txt
set -e
cd "$(dirname "$0")/graph"
J() { java -Xmx8G -cp "$HOME/jars/*" "$@"; }

echo "== Building BVGraph =="
J it.unimi.dsi.webgraph.BVGraph -1 -g ArcListASCIIGraph dummy aid < arclist.txt

echo "== Transposing =="
J it.unimi.dsi.webgraph.Transform transposeOffline aid aid-t
J it.unimi.dsi.webgraph.BVGraph -o -O -L aid
J it.unimi.dsi.webgraph.BVGraph -o -O -L aid-t

echo "== Exact neighbourhood function (parallel BFS) =="
J it.unimi.dsi.webgraph.algo.NeighbourhoodFunction aid | grep -E '^[0-9.eE+]+$' > nf-exact.txt

echo "== HyperBall (log2m=12) =="
J it.unimi.dsi.webgraph.algo.HyperBall -l 12 -n nf-hyperball.txt aid aid-t

echo "== Undirected (symmetrized) distance distribution =="
J it.unimi.dsi.webgraph.Transform symmetrizeOffline aid aid-sym
J it.unimi.dsi.webgraph.BVGraph -o -O -L aid-sym
J it.unimi.dsi.webgraph.algo.NeighbourhoodFunction aid-sym | grep -E '^[0-9.eE+]+$' > nf-sym.txt

echo "== Strongly connected components =="
J it.unimi.dsi.webgraph.algo.StronglyConnectedComponents -s aid
J it.unimi.dsi.webgraph.Stats aid || true

echo "Done. Neighbourhood functions in graph/nf-exact.txt and graph/nf-hyperball.txt"
