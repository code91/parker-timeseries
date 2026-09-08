"""
Section 3 — Spectral analysis and mixing time.

For a row-stochastic operator P, the eigenvalues lie in the closed unit disk
of the complex plane with λ_1 = 1 always present.  The second-largest
modulus |λ_2| governs convergence to π in total-variation distance:
    ||π_t - π||_TV  ≤  C (1 - g)^t,
where g = 1 - |λ_2| is the spectral gap.  Mixing time τ_mix ≈ 1/g is the
characteristic number of steps for the chain to "forget" its initial state.

The slowest-decaying mode is the right eigenvector v_2 corresponding to λ_2:
plotting v_2 coordinates of each state against scale-degree (with marker
shape encoding chord quality and color encoding beat position) reveals
which sub-population of states takes longest to mix.  In a bebop chain we
expect the slow mode to separate dom7 chord tones from approach tones, or
on-beat from off-beat — those are the dimensions with the slowest churn.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from scipy.linalg import eig

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    DATA_DIR,
    FIGURES_DIR,
    load_operator,
    load_state_order,
)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "savefig.dpi": 300,
})

QUALITY_MARKERS = {"maj7": "o", "min7": "s", "dom7": "^", "m7b5": "D", "dim7": "X"}
BEAT_COLORS = {
    "1": "#9b111e",    # strong beats: crimson family
    "2": "#c0392b",
    "3": "#e67e22",
    "4": "#f1c40f",
    "&1": "#2c3e50",   # offbeat: dark blues, one per beat it follows
    "&2": "#34495e",
    "&3": "#4a6785",
    "&4": "#5d8aa8",
}


def spectrum(P: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (eigenvalues, right eigenvectors) sorted by descending |λ|."""
    eigvals, eigvecs = eig(P)
    order = np.argsort(-np.abs(eigvals))
    return eigvals[order], eigvecs[:, order]


def plot_eigenvalues(eigvals: np.ndarray, name: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    # Unit circle for reference
    theta = np.linspace(0, 2 * np.pi, 400)
    ax.plot(np.cos(theta), np.sin(theta), color="grey", linestyle="--", linewidth=0.6)
    ax.axhline(0, color="grey", linewidth=0.4)
    ax.axvline(0, color="grey", linewidth=0.4)
    ax.scatter(eigvals.real, eigvals.imag, s=12, alpha=0.65, color="#3b6fb6",
               edgecolor="black", linewidth=0.2)
    # Highlight λ_1 and λ_2
    ax.scatter([eigvals[0].real], [eigvals[0].imag], s=70, marker="*",
               color="#c0392b", edgecolor="black", linewidth=0.4, label=r"$\lambda_1$")
    ax.scatter([eigvals[1].real], [eigvals[1].imag], s=70, marker="*",
               color="#f39c12", edgecolor="black", linewidth=0.4, label=r"$\lambda_2$")
    gap = 1 - abs(eigvals[1])
    ax.set_title(f"{name}:  spectrum  ($|\\lambda_2|$ = {abs(eigvals[1]):.4f}, gap = {gap:.4f})")
    ax.set_xlabel(r"Re $\lambda$")
    ax.set_ylabel(r"Im $\lambda$")
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_aspect("equal")
    ax.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def plot_v2(v2: np.ndarray, states: list, name: str, out: Path) -> None:
    """Scatter scale-degree on x, Re(v_2) on y; color by beat, marker by quality."""
    v2_real = np.real(v2)
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    for i, (d, q, b) in enumerate(states):
        ax.scatter(
            d, v2_real[i],
            marker=QUALITY_MARKERS[q],
            color=BEAT_COLORS[b],
            s=34, alpha=0.85,
            edgecolor="black", linewidth=0.25,
        )
    ax.axhline(0, color="grey", linewidth=0.5)
    ax.set_xticks(range(12))
    ax.set_xticklabels(["1", "b2", "2", "b3", "3", "4", "#4", "5", "b6", "6", "b7", "7"])
    ax.set_xlabel("Scale degree (semitones above chord root)")
    ax.set_ylabel(r"Re$(v_2)$  —  slowest-decaying mode")
    ax.set_title(f"{name}  —  second eigenvector projected on scale-degree axis")
    # Legend handles
    handles = []
    for q, m in QUALITY_MARKERS.items():
        handles.append(Line2D([0], [0], marker=m, color="w",
                                  markerfacecolor="#7f8c8d", markeredgecolor="black",
                                  markersize=7, label=q))
    for b, c in BEAT_COLORS.items():
        handles.append(Line2D([0], [0], marker="o", color="w",
                                  markerfacecolor=c, markeredgecolor="black",
                                  markersize=7, label=f"beat={b}"))
    ax.legend(handles=handles, ncol=4, loc="upper center",
              bbox_to_anchor=(0.5, -0.15), frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    states = load_state_order()

    summary: dict = {}
    for name in ("P",):
        print(f"\n--- {name} ---")
        P = load_operator(name)
        eigvals, eigvecs = spectrum(P)
        lam1, lam2 = eigvals[0], eigvals[1]
        gap = 1.0 - abs(lam2)
        tau_mix = 1.0 / gap if gap > 0 else float("inf")
        print(f"  λ_1 = {lam1.real:.6f} + {lam1.imag:.2e}i")
        print(f"  λ_2 = {lam2.real:.6f} + {lam2.imag:.2e}i   |λ_2| = {abs(lam2):.4f}")
        print(f"  spectral gap g = {gap:.4f}")
        print(f"  mixing time τ_mix ≈ 1/g = {tau_mix:.2f} steps")

        plot_eigenvalues(eigvals, name, FIGURES_DIR / f"section3_{name}_spectrum")
        plot_v2(eigvecs[:, 1], states, name, FIGURES_DIR / f"section3_{name}_v2")

        summary[name] = {
            "lambda_1": {"re": float(lam1.real), "im": float(lam1.imag)},
            "lambda_2": {"re": float(lam2.real), "im": float(lam2.imag), "abs": float(abs(lam2))},
            "spectral_gap": float(gap),
            "mixing_time_steps": float(tau_mix),
        }
        np.save(DATA_DIR / f"eigvals_{name}.npy", eigvals)

    with (DATA_DIR / "section3_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote eigenvalues, figures, and section3_summary.json")


if __name__ == "__main__":
    main()
