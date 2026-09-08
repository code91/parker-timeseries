"""
Section 5 — Voice-leading recovery (centerpiece).

Joint transition probability under the stationary distribution is
    Pr(X_t = i,  X_{t+1} = j)  =  π_i · P_ij.
Ranking the cells of (π ⊗ P) reveals the most-trafficked transitions,
i.e. Parker's habitual voice-leading moves at and around
chord boundaries.

The canonical V7→I half-step resolution maps to
    (b7, dom7, *)  →  (3, maj7, *).
If this is *not* prominent we have an encoding bug; the sanity check in
Section 0 already confirmed it ranks 6th by raw count, so we expect it
near the top in joint probability as well.
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
    BEAT_POSITIONS,
    DATA_DIR,
    FIGURES_DIR,
    load_operator,
    load_state_order,
    state_label,
)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8,
    "savefig.dpi": 300,
})


def plot_top_transitions(top, states, name: str, out: Path) -> None:
    labels = [f"{state_label(states[i])} → {state_label(states[j])}" for i, j, _, _ in top]
    joints = [j * 100 for _, _, j, _ in top]
    fig, ax = plt.subplots(figsize=(7.0, 6.5))
    y = np.arange(len(labels))
    ax.barh(y, joints, color="#3b6fb6", edgecolor="black", linewidth=0.3)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("Joint probability  π_i · P_ij  (%)")
    ax.set_title(f"{name}:  top 20 transitions by joint probability")
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


V7_TO_I_SOURCES = [(10, "dom7", b) for b in BEAT_POSITIONS]
V7_TO_I_TARGETS = [(4, "maj7", b) for b in BEAT_POSITIONS]


def stationary(P: np.ndarray) -> np.ndarray:
    """Reuse Section 2's algorithm (small inlined copy to avoid a circular import)."""
    from scipy.linalg import eig
    eigvals, eigvecs = eig(P.T)
    idx = int(np.argmin(np.abs(eigvals - 1.0)))
    pi = np.real(eigvecs[:, idx])
    if pi.sum() < 0:
        pi = -pi
    pi = np.clip(pi, 0.0, None)
    return pi / pi.sum()


def top_k_transitions(P: np.ndarray, pi: np.ndarray, k: int = 20):
    """Top-K (i, j, joint, conditional) by joint mass π_i · P_ij."""
    joint = pi[:, None] * P  # outer product on rows
    flat = np.argsort(joint, axis=None)[::-1][:k]
    out = []
    for ix in flat:
        i, j = int(ix // P.shape[0]), int(ix % P.shape[0])
        out.append((i, j, float(joint[i, j]), float(P[i, j])))
    return out


def main() -> None:
    states = load_state_order()
    idx_of = {s: i for i, s in enumerate(states)}

    P_all = load_operator("P")
    pi_all = stationary(P_all)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    top = top_k_transitions(P_all, pi_all, 20)
    plot_top_transitions(top, states, "P", FIGURES_DIR / "section5_P_top20")
    print("\nTop 20 transitions by joint probability (π_i · P_ij):\n")
    print(f"  {'#':>2}  {'source':30s}  {'target':30s}  {'joint':>8}  {'cond':>8}")
    for k, (i, j, joint, cond) in enumerate(top, 1):
        print(f"  {k:>2}  {state_label(states[i]):30s}  -> {state_label(states[j]):30s}  "
              f"{joint*100:>7.3f}%  {cond*100:>7.2f}%")

    # Explicit V7 -> I check
    print("\nV7 -> I cell-by-cell:")
    v7_to_I_rows = []
    for s_src in V7_TO_I_SOURCES:
        for s_tgt in V7_TO_I_TARGETS:
            if s_src in idx_of and s_tgt in idx_of:
                i = idx_of[s_src]; j = idx_of[s_tgt]
                joint = float(pi_all[i] * P_all[i, j])
                cond = float(P_all[i, j])
                v7_to_I_rows.append({"source": state_label(s_src), "target": state_label(s_tgt),
                                     "joint": joint, "conditional": cond})
                print(f"  {state_label(s_src):20s} -> {state_label(s_tgt):20s}  "
                      f"joint = {joint*100:6.3f}%   conditional = {cond*100:6.2f}%")

    summary = {
        "P_top_20": [
            {"rank": k + 1, "source": state_label(states[i]), "target": state_label(states[j]),
             "joint": joint, "conditional": cond}
            for k, (i, j, joint, cond) in enumerate(top)
        ],
        "v7_to_I_cells": v7_to_I_rows,
    }
    with (DATA_DIR / "section5_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote section5_summary.json")


if __name__ == "__main__":
    main()
