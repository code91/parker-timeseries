"""
Section 13 — Where the line resolves to, and how often it comes back.

Two questions Section 4 left open.  Section 4 asked how *long* an unresolved
state takes to reach the resolution set R; it never asked *which* member of R
it reaches, nor how long the walk waits before revisiting a state at all.

1.  Absorption probabilities.  Write T for the 355 unresolved states and R for
    the 73 resolved ones.  Let Q = P[T, T] and P_TR = P[T, R].  Then

        B = (I - Q)^{-1} · P_TR

    and B[i, r] is the probability that, starting from transient state i, the
    FIRST member of R the walk touches is r.  Each row of B sums to 1: with
    smoothing every state escapes, so absorption is certain.

    NB the textbook writes the T -> R block as "R", which collides with R the
    resolution SET used throughout this project.  Hence P_TR.

    This turns voice leading from "how long until resolution" into "resolution
    to what", which is the form a musician would state the rule in.

2.  Mean recurrence time.  For an irreducible positive-recurrent chain, Kac's
    formula gives the expected number of steps to return to state i as

        m_i = 1 / π_i

    so this needs nothing beyond π.  It is the complement of the hitting time:
    hitting time looks forward to a set the walk has not reached, recurrence
    time asks how long the walk waits before playing the same state again.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    DATA_DIR,
    FIGURES_DIR,
    load_operator,
    load_state_order,
    resolution_indices,
    state_label,
    state_label_semitone,
)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "savefig.dpi": 300,
})

N_SOURCES = 6      # unresolved states shown in the absorption figure
N_TARGETS = 4      # resolution targets listed per source


def absorption_matrix(P: np.ndarray, R_idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (B, out_idx): B[i, r] = Pr(first R state reached is R_idx[r] | start at out_idx[i])."""
    n = P.shape[0]
    in_R = np.zeros(n, dtype=bool)
    in_R[R_idx] = True
    out_idx = np.where(~in_R)[0]

    Q = P[np.ix_(out_idx, out_idx)]
    P_TR = P[np.ix_(out_idx, R_idx)]
    B = np.linalg.solve(np.eye(len(out_idx)) - Q, P_TR)
    return B, out_idx


def plot_absorption(rows: list[dict], out: Path) -> None:
    """Stacked bar per source state: where it first resolves to."""
    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    palette = ["#3b6fb6", "#6f9ad3", "#a8c3e4", "#d6e2f2"]

    labels = [r["source"] for r in rows]
    y = np.arange(len(rows))[::-1]

    for i, r in enumerate(rows):
        left = 0.0
        for k, tgt in enumerate(r["targets"][:N_TARGETS]):
            w = tgt["prob"]
            ax.barh(y[i], w, left=left, height=0.62,
                    color=palette[k % len(palette)], edgecolor="white", linewidth=0.6)
            if w > 0.28:
                ax.text(left + w / 2, y[i], f'{tgt["state"]}   {w * 100:.0f} %',
                        ha="center", va="center",
                        fontsize=6.5, color="white" if k < 2 else "#222")
            left += w
        rest = 1.0 - left
        if rest > 0.001:
            ax.barh(y[i], rest, left=left, height=0.62,
                    color="#e8e8e8", edgecolor="white", linewidth=0.6)
            if rest > 0.09:
                ax.text(left + rest / 2, y[i], "all others", ha="center", va="center",
                        fontsize=7.0, color="#666")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_xlabel("segment width = its probability  (row sums to 1)")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def plot_recurrence(m: np.ndarray, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.hist(m, bins=np.logspace(np.log10(m.min()), np.log10(m.max()), 45),
            color="#3b6fb6", edgecolor="black", linewidth=0.3)
    ax.set_xscale("log")
    ax.axvline(float(np.median(m)), color="#c0392b", linestyle="--", linewidth=1.0,
               label=f"median = {np.median(m):.0f} events")
    ax.set_xlabel("expected events until the same state is played again  ($1/\\pi_i$)")
    ax.set_ylabel("# states")
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    states = load_state_order()
    R_idx = resolution_indices(states)
    P = load_operator("P")
    h = np.load(DATA_DIR / "hitting_P.npy")
    pi = np.load(DATA_DIR / "pi_P.npy")

    # ---- 1. absorption -------------------------------------------------
    B, out_idx = absorption_matrix(P, R_idx)
    np.save(DATA_DIR / "absorption_P.npy", B)
    print(f"B is {B.shape[0]} transient x {B.shape[1]} resolved; "
          f"row sums in [{B.sum(axis=1).min():.6f}, {B.sum(axis=1).max():.6f}]")

    order = sorted(range(len(out_idx)), key=lambda i: h[out_idx[i]])[:N_SOURCES]
    rows: list[dict] = []
    print("\nWhere the fastest-resolving states resolve to:")
    for i in order:
        src = states[out_idx[i]]
        tgt_order = np.argsort(-B[i])
        targets = [{"state": state_label_semitone(states[R_idx[r]]), "prob": float(B[i, r])}
                   for r in tgt_order[:N_TARGETS]]
        rows.append({
            "source": state_label_semitone(src),
            "hitting_time": float(h[out_idx[i]]),
            "targets": targets,
        })
        print(f"  {state_label_semitone(src):26s} h={h[out_idx[i]]:.2f}  ->  " +
              ", ".join(f"{t['state']} {t['prob']*100:.1f}%" for t in targets))

    plot_absorption(rows, FIGURES_DIR / "section13_absorption")

    # ---- 2. recurrence -------------------------------------------------
    m = 1.0 / pi
    np.save(DATA_DIR / "recurrence_P.npy", m)
    busiest = np.argsort(-pi)[:5]
    print(f"\nMean recurrence time: median={np.median(m):.1f}  "
          f"min={m.min():.1f}  max={m.max():.1f} events")
    print("Busiest states:")
    for i in busiest:
        print(f"  {state_label(states[i]):26s} pi={pi[i]:.4f}  return every {m[i]:.0f} events")

    plot_recurrence(m, FIGURES_DIR / "section13_recurrence")

    summary = {
        "P": {
            "absorption": {
                "n_transient": int(B.shape[0]),
                "n_resolved": int(B.shape[1]),
                "fastest_sources": rows,
            },
            "recurrence": {
                "median": float(np.median(m)),
                "min": float(m.min()),
                "max": float(m.max()),
                "busiest": [
                    {"state": state_label(states[i]), "pi": float(pi[i]), "recurrence": float(m[i])}
                    for i in busiest
                ],
            },
        }
    }
    with (DATA_DIR / "section13_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    print("\nWrote absorption_P.npy, recurrence_P.npy, figures, and section13_summary.json")


if __name__ == "__main__":
    main()
