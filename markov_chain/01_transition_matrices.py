"""
Section 1 — Transition matrices.

Build three transition operators on the canonical state space:
    P̂          : ML-estimated transition matrix over all in-tune note pairs

Estimator (Laplace-smoothed):
    P̂_ij = (N_ij + α) / (N_i + α · |S|)
with α = SMOOTHING_ALPHA.  Smoothing guarantees full support and exact
row-sums-to-one, eliminating zero-row pathologies in stationary-distribution
and hitting-time computations.

Tune-boundary handling:
    No transition is counted across tune boundaries — we iterate per tune
    and stop one short of the last note within each.

"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    DATA_DIR,
    FIGURES_DIR,
    SMOOTHING_ALPHA,
    UNDERSAMPLED_ROW_THRESHOLD,
    canonical_state_order,
    load_notes,
    save_operator,
    save_state_order,
    state_index_map,
)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "savefig.dpi": 300,
})


def plot_log_heatmap(P: np.ndarray, name: str, out: Path) -> None:
    """log10(P) heatmap with quality-block dividers visible at a glance."""
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(np.log10(P + 1e-12), cmap="magma", aspect="auto",
                   vmin=-4, vmax=0, interpolation="nearest")
    ax.set_title(f"{name}  —  log₁₀ transition probability")
    ax.set_xlabel("destination state index")
    ax.set_ylabel("source state index")
    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label("log₁₀ P̂_ij")
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def build_count_matrices(df: pd.DataFrame, idx: dict) -> np.ndarray:
    """Return the count matrix N.  Transitions are counted per tune, stopping
    one short of each tune's last event, so nothing is counted across a
    boundary between solos."""
    n = len(idx)
    N = np.zeros((n, n), dtype=np.int64)
    for tune_id, grp in df.groupby("tune_id", sort=False):
        states_t = grp["state"].tolist()
        for t in range(len(states_t) - 1):
            N[idx[states_t[t]], idx[states_t[t + 1]]] += 1
    return N


def smooth_to_stochastic(N: np.ndarray, alpha: float) -> np.ndarray:
    """Laplace-smoothed row-stochastic matrix.  Every row sums to exactly 1."""
    n = N.shape[0]
    smoothed = N.astype(np.float64) + alpha
    row_sums = smoothed.sum(axis=1, keepdims=True)
    return smoothed / row_sums


def report(name: str, N: np.ndarray, P: np.ndarray) -> dict:
    n = N.shape[0]
    total_transitions = int(N.sum())
    nonzero_cells = int((N > 0).sum())
    sparsity_pct = 100 * (1 - nonzero_cells / (n * n))
    row_sample_sizes = N.sum(axis=1)
    undersampled = int((row_sample_sizes < UNDERSAMPLED_ROW_THRESHOLD).sum())
    row_sum_max_err = float(np.abs(P.sum(axis=1) - 1.0).max())

    print(f"\n  {name}")
    print(f"    transitions counted    : {total_transitions:,}")
    print(f"    nonzero count cells    : {nonzero_cells:,} / {n*n:,}")
    print(f"    sparsity               : {sparsity_pct:.2f}%")
    print(f"    rows with N_i = 0      : {int((row_sample_sizes == 0).sum())}")
    print(f"    rows with N_i < {UNDERSAMPLED_ROW_THRESHOLD:<3d}   : {undersampled}")
    print(f"    row N_i  median={np.median(row_sample_sizes):.0f}  "
          f"min={int(row_sample_sizes.min())}  max={int(row_sample_sizes.max())}")
    print(f"    row-sum verification   : max|sum(P_i) - 1| = {row_sum_max_err:.2e}")

    return {
        "operator": name,
        "n_states": n,
        "total_transitions": total_transitions,
        "nonzero_cells": nonzero_cells,
        "sparsity_pct": sparsity_pct,
        "rows_with_zero_count": int((row_sample_sizes == 0).sum()),
        "rows_undersampled": undersampled,
        "row_sample_size_median": float(np.median(row_sample_sizes)),
        "row_sum_max_error": row_sum_max_err,
    }


def main() -> None:
    print("Loading per-note dataset ...")
    df = load_notes()
    print(f"  {len(df):,} notes, {df['tune_id'].nunique()} tunes")

    states = canonical_state_order(df["state"])
    idx = state_index_map(states)
    print(f"\nObserved state space |S| = {len(states)}")

    print("\nBuilding count matrices ...")
    N_all = build_count_matrices(df, idx)

    print("\nLaplace smoothing (alpha = "
          f"{SMOOTHING_ALPHA}) and conversion to row-stochastic form ...")
    P_all = smooth_to_stochastic(N_all, SMOOTHING_ALPHA)

    reports = []
    reports.append(report("P (all transitions)", N_all, P_all))

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plot_log_heatmap(P_all, "P (all transitions)", FIGURES_DIR / "section1_P_logheatmap")

    # Persist
    save_state_order(states)
    save_operator("P", P_all)
    # Also persist raw counts for downstream tests (null comparison, χ²).
    np.save(DATA_DIR / "N.npy", N_all)

    summary_path = DATA_DIR / "section1_summary.json"
    with summary_path.open("w") as f:
        json.dump(reports, f, indent=2)
    print(f"\nWrote operators, counts, states.json, and {summary_path.name}")


if __name__ == "__main__":
    main()
