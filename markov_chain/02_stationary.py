"""
Section 2 — Stationary distributions.

For a row-stochastic matrix P, the stationary distribution π satisfies
    π P = π,    Σ π = 1,    π ≥ 0.
By Perron-Frobenius, an irreducible aperiodic chain has a unique strictly
positive π.  Laplace smoothing (Section 1) makes every operator irreducible
and aperiodic, so π exists and is unique.

We compute π by diagonalizing P.T:
    P.T  v = λ v       (v is a right eigenvector of P.T)
    π    = v_{λ=1}     (corresponding to λ closest to 1)
    π   ← π / Σπ       (ℓ¹-normalization, with sign-fix if needed)

We verify πP ≈ π and compare π against the empirical state-frequency
distribution f(s) = (# notes in state s) / (total notes).  Pearson r
quantifies how well the stationary distribution recovers the empirical
marginal — high r means the chain is well-mixed enough that its long-run
occupation matches what we actually observe.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.linalg import eig
from scipy.stats import pearsonr

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    DATA_DIR,
    FIGURES_DIR,
    load_notes,
    load_operator,
    load_state_order,
    state_label,
)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "savefig.dpi": 300,
    "figure.constrained_layout.use": False,
})


def stationary_distribution(P: np.ndarray) -> np.ndarray:
    """Left eigenvector at λ=1, ℓ¹-normalized."""
    eigvals, eigvecs = eig(P.T)
    # Pick eigenvalue closest to 1
    idx = int(np.argmin(np.abs(eigvals - 1.0)))
    pi = np.real(eigvecs[:, idx])
    # Sign-fix and normalize
    if pi.sum() < 0:
        pi = -pi
    pi = np.clip(pi, 0.0, None)
    pi = pi / pi.sum()
    return pi


def empirical_distribution(df: pd.DataFrame, states: list) -> np.ndarray:
    """Empirical marginal over the canonical state order."""
    counts = df["state"].value_counts()
    f = np.zeros(len(states), dtype=np.float64)
    for i, s in enumerate(states):
        f[i] = counts.get(s, 0)
    return f / f.sum()


def verify_stationary(P: np.ndarray, pi: np.ndarray) -> float:
    """Return max|πP - π|."""
    return float(np.abs(pi @ P - pi).max())


def plot_stationary_vs_empirical(
    pi: np.ndarray, f: np.ndarray, name: str, out: Path
) -> None:
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    ax.scatter(f, pi, s=14, alpha=0.65, edgecolor="black", linewidth=0.3, color="#3b6fb6")
    lim = max(pi.max(), f.max()) * 1.05
    ax.plot([0, lim], [0, lim], color="grey", linestyle="--", linewidth=0.8, label="y = x")
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_xlabel("Empirical frequency")
    ax.set_ylabel("Stationary probability  π")
    r, _ = pearsonr(f, pi)
    ax.set_title(f"{name}:  Pearson r = {r:.4f}")
    ax.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def top_k_states(pi: np.ndarray, states: list, k: int = 10) -> list[tuple[str, float]]:
    order = np.argsort(-pi)[:k]
    return [(state_label(states[i]), float(pi[i])) for i in order]


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    states = load_state_order()
    df = load_notes()
    f_emp = empirical_distribution(df, states)

    summary: dict = {}
    for name in ("P",):
        print(f"\n--- {name} ---")
        P = load_operator(name)
        pi = stationary_distribution(P)
        residual = verify_stationary(P, pi)
        r, p = pearsonr(f_emp, pi)
        print(f"  Σπ = {pi.sum():.6f}    min π = {pi.min():.2e}")
        print(f"  max|πP - π| = {residual:.2e}")
        print(f"  Pearson r vs empirical = {r:.4f}  (p = {p:.2e})")
        top = top_k_states(pi, states, 10)
        print(f"  Top 10 high-mass states:")
        for label, mass in top:
            print(f"    {label:30s}  π = {mass:.4f}")

        plot_stationary_vs_empirical(pi, f_emp, name, FIGURES_DIR / f"section2_{name}_pi_vs_empirical")
        np.save(DATA_DIR / f"pi_{name}.npy", pi)
        summary[name] = {
            "residual_max": residual,
            "pearson_r_vs_empirical": float(r),
            "pearson_p_vs_empirical": float(p),
            "min_pi": float(pi.min()),
            "top_10": [{"state": s, "pi": m} for s, m in top],
        }

    with (DATA_DIR / "section2_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote pi_*.npy, figures, and section2_summary.json")


if __name__ == "__main__":
    main()
