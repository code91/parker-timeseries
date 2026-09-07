"""
Section 10 — Evolving the probability distribution.

The exam task asks for the distribution over nodes to be evolved directly,
starting concentrated on a single node:

    mu_0 = e_i            all probability on one state
    mu_{t+1} = mu_t P     one step of the chain

and for that evolution to be watched converging on the stationary
distribution pi.  Section 2 obtains pi algebraically as the left eigenvector
at lambda = 1; this section obtains it the other way, by iteration, and shows
the two agree.  It also turns the mixing time of Section 3 from an assertion
(1 / spectral gap) into something measured: the total-variation distance
TV(mu_t, pi) should decay like |lambda_2|^t.

Writes data/section10_summary.json and figures/section10_*.
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
    state_label,
)

ACCENT = "#9b111e"
BLUE = "#3b6fb6"
INK = "#1a1a1a"
MUTED = "#8c8c8c"
T_STEPS = 40
SNAPSHOTS = (0, 1, 2, 5, 20)

plt.rcParams.update({"font.family": "serif", "font.size": 9, "savefig.dpi": 300})


def tv(a: np.ndarray, b: np.ndarray) -> float:
    return 0.5 * float(np.abs(a - b).sum())


def main() -> None:
    states = load_state_order()
    P = load_operator("P")
    pi = np.load(DATA_DIR / "pi_P.npy")
    n = len(states)

    # start on the busiest state, so the walk begins somewhere Parker really is
    start = int(np.argmax(pi))
    mu = np.zeros(n)
    mu[start] = 1.0

    traj, dists = [mu.copy()], [tv(mu, pi)]
    for _ in range(T_STEPS):
        mu = mu @ P
        traj.append(mu.copy())
        dists.append(tv(mu, pi))
    dists = np.array(dists)

    lam2 = float(np.abs(np.load(DATA_DIR / "eigvals_P.npy"))[1])
    half = int(np.argmax(dists < 0.5)) if (dists < 0.5).any() else -1
    within_1pct = int(np.argmax(dists < 0.01)) if (dists < 0.01).any() else -1

    plot(traj, dists, pi, states, start, lam2, FIGURES_DIR / "section10_distribution_evolution")

    summary = {
        "start_state": state_label(states[start]),
        "steps": T_STEPS,
        "tv_by_step": [float(x) for x in dists],
        "steps_to_tv_below_0.5": half,
        "steps_to_tv_below_0.01": within_1pct,
        "lambda_2_abs": lam2,
        "max_abs_diff_mu_T_vs_pi": float(np.abs(traj[-1] - pi).max()),
    }
    with (DATA_DIR / "section10_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"start state          : {summary['start_state']}")
    print(f"TV(mu_t, pi) reaches 0.5 after {half} steps, 0.01 after {within_1pct} steps")
    print(f"|mu_{T_STEPS} - pi|_max      : {summary['max_abs_diff_mu_T_vs_pi']:.2e}")
    print(f"decay rate |lambda_2| : {lam2:.4f}")
    print("Wrote section10_summary.json and figures")


def plot(traj, dists, pi, states, start, lam2, out: Path) -> None:
    fig, (ax_tv, ax_snap) = plt.subplots(1, 2, figsize=(11.0, 3.8), width_ratios=[1.0, 1.35])

    t = np.arange(len(dists))
    ax_tv.semilogy(t, dists, color=ACCENT, linewidth=1.4, marker="o", markersize=2.5,
                   label=r"TV($\mu_t$, $\pi$)")
    ax_tv.semilogy(t, dists[0] * lam2 ** t, color=MUTED, linestyle="--", linewidth=1.0,
                   label=rf"$|\lambda_2|^t$  ({lam2:.3f})")
    ax_tv.set_xlabel("step $t$"); ax_tv.set_ylabel("total-variation distance to $\\pi$")
    ax_tv.set_title("The distribution converges at the rate the spectrum predicts",
                    fontsize=10, pad=8)
    ax_tv.legend(frameon=False, fontsize=8)
    ax_tv.spines[["top", "right"]].set_visible(False)

    # snapshots over the states that carry the most stationary mass
    order = np.argsort(pi)[::-1][:14]
    x = np.arange(len(order))
    for k, s in enumerate(SNAPSHOTS):
        ax_snap.plot(x, traj[s][order], marker="o", markersize=3, linewidth=1.0,
                     alpha=0.85, label=f"$\\mu_{{{s}}}$")
    ax_snap.plot(x, pi[order], color=INK, linestyle="--", linewidth=1.4, label=r"$\pi$")
    ax_snap.set_yscale("log")
    ax_snap.set_xticks(x, [state_label(states[i]) for i in order], rotation=90, fontsize=6)
    ax_snap.set_ylabel("probability")
    ax_snap.set_title("From all the mass on one state, to $\\pi$", fontsize=10, pad=8)
    ax_snap.legend(frameon=False, fontsize=7.5, ncol=3)
    ax_snap.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(out.with_suffix(".png")); fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


if __name__ == "__main__":
    main()
