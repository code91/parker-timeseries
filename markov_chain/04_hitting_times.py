"""
Section 4 — Hitting times to the resolution set R.

Definition.  R = {(d, q, "on") : d in CHORD_TONES[q]} is the strong-beat
chord-tone slice of the state space.  In bebop interpretation, reaching R
means "the melody has landed on a chord tone on a downbeat" — i.e. the
phrase has resolved.

For any state i ∉ R, the expected number of steps to first reach R is
    h(i) = 1 + Σ_{j ∉ R} P_ij · h(j),
    h(j) = 0  for j ∈ R.
Let Q be the principal sub-block of P on states outside R.  Then
    h = (I - Q)^{-1} · 1.
Laplace smoothing guarantees positive escape probability from every state,
so I - Q is invertible and h is finite, positive, and unique.

Interpretation:  h(i) is the "harmonic distance" from i to resolution,
measured in note-events.  Chromatic / approach states should have short h;
states that wander far from the chord (e.g. tritone over maj7 on an
off-beat) should have long h.  This recovers musical *gravity* as an
expected-time computation.
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
    is_chord_tone_state,
    load_operator,
    load_state_order,
    resolution_indices,
    state_label,
)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "savefig.dpi": 300,
})


def hitting_times(P: np.ndarray, R_idx: np.ndarray) -> np.ndarray:
    """Return h of length n: h[i] = E[steps to hit R | X_0 = i].  h[i]=0 for i in R."""
    n = P.shape[0]
    in_R = np.zeros(n, dtype=bool)
    in_R[R_idx] = True
    out_idx = np.where(~in_R)[0]

    Q = P[np.ix_(out_idx, out_idx)]
    rhs = np.ones(len(out_idx))
    h_out = np.linalg.solve(np.eye(len(out_idx)) - Q, rhs)

    h = np.zeros(n)
    h[out_idx] = h_out
    return h


def plot_hitting_distribution(h: np.ndarray, R_idx: np.ndarray, name: str, out: Path) -> None:
    n = h.shape[0]
    mask = np.ones(n, dtype=bool)
    mask[R_idx] = False
    h_out = h[mask]
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    ax.hist(h_out, bins=40, color="#3b6fb6", edgecolor="black", linewidth=0.3)
    ax.axvline(np.median(h_out), color="#c0392b", linestyle="--", linewidth=1.0,
               label=f"median = {np.median(h_out):.2f}")
    ax.set_xlabel("Expected hitting time to R  (note-events)")
    ax.set_ylabel("# states")
    ax.set_title(f"{name}  —  hitting-time distribution over states outside R "
                 f"(|R| = {len(R_idx)}, |S\\R| = {len(h_out)})")
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    states = load_state_order()
    R_idx = resolution_indices(states)
    print(f"Resolution set R: {len(R_idx)} states out of {len(states)}")
    print("R members (chord-tone, on-beat):")
    for i in R_idx:
        print(f"  {state_label(states[i])}")

    summary: dict = {}
    for name in ("P", "P_within", "P_across"):
        print(f"\n--- {name} ---")
        P = load_operator(name)
        h = hitting_times(P, R_idx)
        np.save(DATA_DIR / f"hitting_{name}.npy", h)

        mask = np.ones(len(states), dtype=bool); mask[R_idx] = False
        h_out = h[mask]
        print(f"  h over S\\R:  median={np.median(h_out):.2f}  mean={h_out.mean():.2f}  "
              f"max={h_out.max():.2f}  min={h_out.min():.2f}")

        # Top 8 shortest and longest hitting times for inspection.
        out_states = [(i, states[i], h[i]) for i in range(len(states)) if not is_chord_tone_state(states[i])]
        out_states.sort(key=lambda x: x[2])
        print("  Shortest 8 hitting times (gravity sinks adjacent to R):")
        for i, s, hv in out_states[:8]:
            print(f"    {state_label(s):30s}  h = {hv:.2f}")
        print("  Longest 8 hitting times (musically remote):")
        for i, s, hv in out_states[-8:]:
            print(f"    {state_label(s):30s}  h = {hv:.2f}")

        plot_hitting_distribution(h, R_idx, name, FIGURES_DIR / f"section4_{name}_hitting")

        summary[name] = {
            "n_R": int(len(R_idx)),
            "n_out_R": int(len(h_out)),
            "h_median": float(np.median(h_out)),
            "h_mean": float(h_out.mean()),
            "h_min": float(h_out.min()),
            "h_max": float(h_out.max()),
            "shortest_8": [{"state": state_label(s), "h": float(hv)} for _, s, hv in out_states[:8]],
            "longest_8": [{"state": state_label(s), "h": float(hv)} for _, s, hv in out_states[-8:]],
        }

    with (DATA_DIR / "section4_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote hitting_*.npy, figures, and section4_summary.json")


if __name__ == "__main__":
    main()
