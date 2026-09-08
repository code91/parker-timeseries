"""
Section 11 — The chain as a graph.

The exam task is posed on a small graph of 6-8 nodes.  The full operator has
428, so this section draws the induced subgraph on the eight states that carry
the most stationary mass: a legible picture of the same random walk, with the
real transition probabilities on the edges.

Node area is proportional to pi, edge width and opacity to P_ij, and the
arrows show that the walk is directed (P is not symmetric: the corpus has
4,643 one-way edges against 778 reciprocated ones).

PageRank is recomputed on the subgraph so the ordering can be compared with
the full-graph ranking from Section 8.

Writes data/section11_summary.json and figures/section11_*.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    DATA_DIR,
    FIGURES_DIR,
    load_operator,
    load_state_order,
    REST_SD,
    scale_degree_name,
)

K = 8
MIN_EDGE = 0.02          # hide weak edges, but never orphan a node (see below)
ACCENT = "#9b111e"
INK = "#1a1a1a"
SOFT = "#f4e1e3"

plt.rcParams.update({"font.family": "serif", "font.size": 9, "savefig.dpi": 300})


def main() -> None:
    states = load_state_order()
    P = load_operator("P")
    pi = np.load(DATA_DIR / "pi_P.npy")
    N = np.load(DATA_DIR / "N.npy")

    top = list(np.argsort(pi)[::-1][:K])
    # semitone plus musician name, matching the matrix excerpt: "9 (6), dom7, b4"
    def label(i: int) -> str:
        d, q, b = states[i]
        deg = REST_SD if d == REST_SD else f"{d} ({scale_degree_name(d)})"
        return f"{deg}, {q}, {b if b.startswith('&') else 'b' + b}"

    labels = {i: label(i) for i in top}

    G = nx.DiGraph()
    for i in top:
        G.add_node(i, pi=float(pi[i]))
    # Keep every edge above the threshold, and additionally always keep each
    # node's strongest outgoing edge, so no node is left orphaned in a picture
    # whose whole point is that it is a connected walk.
    kept = 0
    for i in top:
        others = [j for j in top if j != i]
        strongest = max(others, key=lambda j: P[i, j])
        for j in others:
            if P[i, j] >= MIN_EDGE or j == strongest:
                G.add_edge(i, j, p=float(P[i, j]), n=int(N[i, j]))
                kept += 1

    pr = nx.pagerank(G, alpha=0.85, weight="p")
    plot(G, top, labels, pi, FIGURES_DIR / "section11_graph_view")

    mass = float(pi[top].sum())
    summary = {
        "k_nodes": K,
        "min_edge_shown": MIN_EDGE,
        "edges_shown": kept,
        "edges_possible": K * (K - 1),
        "stationary_mass_covered": mass,
        "nodes": [
            {"state": labels[i], "pi": float(pi[i]), "pagerank_subgraph": float(pr[i])}
            for i in sorted(top, key=lambda x: -pr[x])
        ],
        "strongest_edges": sorted(
            [{"from": labels[u], "to": labels[v], "p": d["p"], "n": d["n"]}
             for u, v, d in G.edges(data=True)],
            key=lambda e: -e["p"])[:6],
    }
    with (DATA_DIR / "section11_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"top {K} states carry {100*mass:.1f} % of the stationary mass")
    print(f"edges at or above {MIN_EDGE:.0%}: {kept} of {K*(K-1)} possible")
    for e in summary["strongest_edges"]:
        print(f"  {e['from']:22} -> {e['to']:22} {e['p']*100:5.1f} %  (n={e['n']})")
    print("Wrote section11_summary.json and figures")


def plot(G, top, labels, pi, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.0, 4.8))
    pos = nx.circular_layout(G)
    sizes = [2300 * pi[i] / pi[top].max() for i in G.nodes]
    nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color=SOFT,
                           edgecolors=ACCENT, linewidths=1.2, ax=ax)
    widths = [0.6 + 26.0 * G[u][v]["p"] for u, v in G.edges]
    nx.draw_networkx_edges(G, pos, width=widths, edge_color=INK, alpha=0.45,
                           arrowsize=11, connectionstyle="arc3,rad=0.10",
                           node_size=sizes, ax=ax)
    nx.draw_networkx_labels(G, pos, labels={i: labels[i].replace(", ", ",\n") for i in G.nodes},
                            font_size=6, font_family="serif", ax=ax)
    edge_lab = {(u, v): f"{G[u][v]['p']*100:.0f}" for u, v in G.edges}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_lab, font_size=6,
                                 font_family="serif", label_pos=0.35,
                                 bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.7),
                                 ax=ax)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png")); fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


if __name__ == "__main__":
    main()
