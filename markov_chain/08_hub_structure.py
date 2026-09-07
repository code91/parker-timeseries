"""
Section 8 — Hub and graph structure.

Treat each smoothed transition matrix as a weighted directed graph
G = (V, E, w) with w_ij = P_ij and edges restricted to cells with raw
count N_ij > 0 (to ignore smoothed-only edges).  Compute four centralities:

  PageRank (damped):
    r = (1 - d)/n · 1  +  d · P^T · r,   d = 0.85.
    Distinct from the stationary π because teleportation softens the
    long-run distribution.  Highlights states that receive incoming
    traffic from many other influential states.

  Weighted in-degree:
    deg_in(j)  = Σ_i N_ij.
    Raw incoming traffic — how often the chain lands on j.

  Weighted out-degree:
    deg_out(i) = Σ_j N_ij.
    Raw outgoing traffic.

  Betweenness centrality:
    Shortest-path centrality using edge weight w'_ij = -log P_ij (so a
    high-probability edge is short).  A state is between two others if
    it lies on many shortest paths — i.e. it is a "pivot" the chain
    routes through.

Cross-tabulation: report, for each metric's top 10 states, how many are
  chord-tone states (in CHORD_TONES[q]) vs approach tones, and how many
  are on-beat vs off-beat.
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
    CHORD_TONES,
    DATA_DIR,
    FIGURES_DIR,
    STRONG_BEATS,
    is_rest_state,
    load_operator,
    load_state_order,
    state_label,
)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8,
    "savefig.dpi": 300,
})


def plot_top_pagerank(per_op: dict, out: Path) -> None:
    """3-panel horizontal-bar plot: top-10 PageRank per operator."""
    fig, axes = plt.subplots(1, 3, figsize=(11.0, 4.8), sharex=False)
    for ax, (name, vals) in zip(axes, per_op.items()):
        labels = [row["state"] for row in vals]
        scores = [row["value"] for row in vals]
        y = np.arange(len(labels))
        ax.barh(y, scores, color="#3b6fb6", edgecolor="black", linewidth=0.3)
        ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("PageRank")
        ax.set_title(name)
    fig.suptitle("Section 8 — top-10 hubs by damped PageRank (d = 0.85)")
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)

DAMPING = 0.85
EPSILON = 1e-12


def build_graph(P: np.ndarray, N: np.ndarray) -> nx.DiGraph:
    """Directed graph on observed edges (N_ij > 0); attributes 'prob' and 'count'."""
    n = P.shape[0]
    G = nx.DiGraph()
    for i in range(n):
        G.add_node(i)
    for i in range(n):
        for j in range(n):
            if N[i, j] > 0:
                G.add_edge(
                    i, j,
                    prob=float(P[i, j]),
                    count=int(N[i, j]),
                    distance=-np.log(P[i, j] + EPSILON),
                )
    return G


def pagerank_damped(P: np.ndarray, d: float = DAMPING, tol: float = 1e-12, max_iter: int = 10_000) -> np.ndarray:
    n = P.shape[0]
    r = np.full(n, 1.0 / n)
    teleport = np.full(n, (1.0 - d) / n)
    Pt = P.T
    for _ in range(max_iter):
        r_new = teleport + d * (Pt @ r)
        if np.abs(r_new - r).max() < tol:
            r = r_new
            break
        r = r_new
    return r / r.sum()


def chord_tone_breakdown(top_states, states) -> dict:
    """Breakdown over the new (v2) state space.  Rests contribute neither to
    chord-tone nor approach-tone counts (they are silence); 'strong_beat' counts
    hits on any of beats 1-4, 'off_grid' counts the '&' positions."""
    n_chord = sum(
        1 for i in top_states
        if not is_rest_state(states[i]) and states[i][0] in CHORD_TONES[states[i][1]]
    )
    n_rest = sum(1 for i in top_states if is_rest_state(states[i]))
    n_strong = sum(1 for i in top_states if states[i][2] in STRONG_BEATS)
    return {
        "n_chord_tone": n_chord,
        "n_approach_tone": len(top_states) - n_chord - n_rest,
        "n_rest": n_rest,
        "n_strong_beat": n_strong,
        "n_off_grid": len(top_states) - n_strong,
    }


def main() -> None:
    states = load_state_order()
    summary: dict = {}

    for name in ("P", "P_within", "P_across"):
        print(f"\n--- {name} ---")
        P = load_operator(name)
        count_name = "N" if name == "P" else "N_" + name[len("P_"):]
        N = np.load(DATA_DIR / f"{count_name}.npy")
        G = build_graph(P, N)
        print(f"  graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges (observed-count > 0)")

        pr = pagerank_damped(P)
        deg_in = N.sum(axis=0).astype(np.float64)
        deg_out = N.sum(axis=1).astype(np.float64)
        # Betweenness is expensive on large dense graphs; we have ~119 nodes so fine.
        bc = nx.betweenness_centrality(G, weight="distance", normalized=True)
        bc_arr = np.array([bc.get(i, 0.0) for i in range(len(states))])

        metrics = {
            "PageRank": pr,
            "weighted_in_degree": deg_in,
            "weighted_out_degree": deg_out,
            "betweenness": bc_arr,
        }

        per_metric: dict = {}
        for mname, values in metrics.items():
            order = np.argsort(-values)[:10]
            print(f"\n  Top 10 by {mname}:")
            rows = []
            for rank, i in enumerate(order, 1):
                lbl = state_label(states[int(i)])
                print(f"    {rank:>2}. {lbl:30s}  {values[int(i)]:>10.4f}")
                rows.append({"rank": rank, "state": lbl, "value": float(values[int(i)])})
            bd = chord_tone_breakdown([int(i) for i in order], states)
            print(f"     breakdown: chord-tone={bd['n_chord_tone']}/10  "
                  f"approach={bd['n_approach_tone']}/10  "
                  f"rest={bd['n_rest']}/10  "
                  f"strong-beat={bd['n_strong_beat']}/10  off-grid={bd['n_off_grid']}/10")
            per_metric[mname] = {"top_10": rows, "breakdown": bd}

        summary[name] = {
            "n_nodes": G.number_of_nodes(),
            "n_edges": G.number_of_edges(),
            "metrics": per_metric,
        }

    with (DATA_DIR / "section8_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    per_op_pr = {name: summary[name]["metrics"]["PageRank"]["top_10"]
                 for name in ("P", "P_within", "P_across")}
    plot_top_pagerank(per_op_pr, FIGURES_DIR / "section8_top10_pagerank")
    print(f"\nWrote section8_summary.json and figures")


if __name__ == "__main__":
    main()
