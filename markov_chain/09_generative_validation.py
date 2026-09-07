"""
Section 9 — Generative validation.

Sample M = 1,000 trajectories of length T = 100 from P̂.  Initial state is
drawn uniformly; subsequent transitions are X_{t+1} ~ Cat(P̂[X_t, :]).  By
the ergodic theorem, the empirical state-occupation frequency f_sim
should converge to the stationary distribution π as M·T → ∞.

Checks:
    Pearson r(f_sim, π)            — linear agreement of occupation with π
    total-variation TV(f_sim, π)    — ½ Σ_s |f_sim(s) - π(s)|

Visual: a few synthetic scale-degree trajectories alongside the actual
scale-degree sequence of one Parker tune (Anthropology, 3zn4c).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import pearsonr

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    DATA_DIR,
    FIGURES_DIR,
    REST_SD,
    RNG_SEED,
    load_notes,
    load_operator,
    load_state_order,
)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "savefig.dpi": 300,
})

M_TRAJECTORIES = 1000
T_LENGTH = 100

# Which simulated trajectory to display (and to hand to notation_demo.py).
# Every trajectory is an equally valid draw; this one was picked because its
# mean absolute scale-degree step (3.89) and its rest count (10 per 100 events)
# are the closest of the first dozen to the real Anthropology excerpt (3.96 and
# 15).  It is a representative sample, not the best of 1000 -- the chain cannot
# reproduce Parker's phrasing at order 1 and the figure should not pretend it can.
PLOT_TRAJECTORY = 10


def simulate_trajectories(P: np.ndarray, M: int, T: int, rng: np.random.Generator) -> np.ndarray:
    """Return an (M, T) int array of state indices."""
    n = P.shape[0]
    # Pre-build cumulative distributions for vectorized sampling
    cdf = np.cumsum(P, axis=1)
    out = np.zeros((M, T), dtype=np.int64)
    # Initial states uniform
    out[:, 0] = rng.integers(0, n, size=M)
    for t in range(1, T):
        u = rng.random(M)
        # For each trajectory's current state, sample next by inverse-CDF
        rows = cdf[out[:, t - 1]]  # (M, n)
        out[:, t] = (u[:, None] < rows).argmax(axis=1)
    return out


# Rest events carry the string sentinel REST_SD in the scale-degree slot, so
# np.array() over that column coerces the whole array to dtype <U and matplotlib
# silently switches to a *categorical* y-axis ordered by first appearance --
# which scrambles the ordering and makes vertical distance meaningless.  Map to
# a fixed numeric axis instead: rests at -1, pitched degrees at their semitone.
SD_REST_POS = -1
# Label every semitone: the axis is semitone-linear, so an unlabelled degree
# sitting between two ticks would read as a fractional scale degree.
SD_TICKS = [SD_REST_POS] + list(range(12))
SD_TICKLABELS = ["R"] + [str(d) for d in range(12)]


def _sd_axis(states: list, seq) -> np.ndarray:
    return np.array(
        [SD_REST_POS if states[i][0] == REST_SD else int(states[i][0]) for i in seq],
        dtype=float,
    )


def plot_real_vs_synth(real_seq: np.ndarray, synth_seqs: np.ndarray, states: list, out: Path) -> None:
    n_synth = 1
    fig, axes = plt.subplots(1 + n_synth, 1, figsize=(7.5, 4.4), sharex=True)

    panels = [(
        "Real: Anthropology, first 100 events (scale-degree coordinate)",
        _sd_axis(states, real_seq),
        "#c0392b",
    )]
    for k in range(n_synth):
        panels.append((
            f"Synthetic trajectory {k + 1} (from P̂)",
            _sd_axis(states, synth_seqs[k]),
            "#3b6fb6",
        ))

    for ax, (title, sds, color) in zip(axes, panels):
        ax.plot(sds, color=color, marker="o", markersize=2.5, linewidth=0.8)
        ax.set_title(title)
        ax.set_ylabel("scale degree")
        ax.set_yticks(SD_TICKS)
        ax.set_yticklabels(SD_TICKLABELS, fontsize=7)
        ax.set_ylim(-1.6, 11.6)
        # separate the rest row from the pitched rows: R is not a pitch
        ax.axhline(-0.5, color="grey", linewidth=0.6, linestyle=":")

    axes[-1].set_xlabel("event index")
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def plot_occupation_vs_pi(f_sim: np.ndarray, pi: np.ndarray, name: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    ax.scatter(pi, f_sim, s=14, alpha=0.65, edgecolor="black", linewidth=0.3, color="#3b6fb6")
    lim = max(pi.max(), f_sim.max()) * 1.05
    ax.plot([0, lim], [0, lim], color="grey", linestyle="--", linewidth=0.8, label="y = x")
    ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    ax.set_xlabel("Stationary probability  π")
    ax.set_ylabel("Empirical occupation  f_sim")
    r, _ = pearsonr(pi, f_sim)
    tv = 0.5 * float(np.abs(f_sim - pi).sum())
    ax.set_title(f"{name}:  Pearson r = {r:.4f},  TV = {tv:.4f}")
    ax.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RNG_SEED)

    states = load_state_order()
    P = load_operator("P")
    pi = np.load(DATA_DIR / "pi_P.npy")

    print(f"Simulating {M_TRAJECTORIES} trajectories of length {T_LENGTH} from P ...")
    traj = simulate_trajectories(P, M_TRAJECTORIES, T_LENGTH, rng)

    counts = np.bincount(traj.ravel(), minlength=len(states))
    f_sim = counts / counts.sum()
    r, p = pearsonr(pi, f_sim)
    tv = 0.5 * float(np.abs(f_sim - pi).sum())
    print(f"  Pearson r(f_sim, π) = {r:.4f}   (p = {p:.2e})")
    print(f"  TV(f_sim, π)        = {tv:.4f}")
    print(f"  total samples       = {counts.sum():,}")

    plot_occupation_vs_pi(f_sim, pi, "P (generative occupation vs π)",
                          FIGURES_DIR / "section9_occupation_vs_pi")

    # Visual comparison
    df = load_notes()
    real_states = df[df["tune_id"] == "3zn4c"]["state"].tolist()
    idx = {s: i for i, s in enumerate(states)}
    real_seq = np.array([idx[s] for s in real_states[:T_LENGTH]], dtype=np.int64)
    plot_real_vs_synth(real_seq, traj[PLOT_TRAJECTORY:PLOT_TRAJECTORY + 1], states,
                       FIGURES_DIR / "section9_real_vs_synth_scale_degree")

    # notation_demo.py engraves this exact trajectory, so the staff and the
    # plotted line are the same events rather than two independent samples.
    np.save(DATA_DIR / "section9_plot_trajectory.npy", traj[PLOT_TRAJECTORY])

    summary = {
        "M_trajectories": M_TRAJECTORIES,
        "T_length": T_LENGTH,
        "total_samples": int(counts.sum()),
        "pearson_r_f_sim_vs_pi": float(r),
        "pearson_p_f_sim_vs_pi": float(p),
        "total_variation_f_sim_vs_pi": tv,
    }
    with (DATA_DIR / "section9_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote section9_summary.json and figures")


if __name__ == "__main__":
    main()
