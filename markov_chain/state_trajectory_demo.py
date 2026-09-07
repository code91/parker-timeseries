"""
The trajectory as it actually is: one step, one state.

The teaser on the framing slide plots only the scale-degree coordinate, which
collapses 5 chord qualities x 8 beat positions onto each point.  This figure
plots the state index itself, so every step is the whole triple.

The canonical state ordering is (quality, scale degree, beat), so the y-axis
is blocked by chord quality; those blocks are shaded and labelled.  Reading
it: vertical position inside a block is scale degree, and a jump between
blocks is a chord-quality change.

Standalone: run after 09_generative_validation.py, which writes the
trajectory that the synthetic panel replays.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    DATA_DIR,
    FIGURES_DIR,
    STRONG_BEATS,
    load_notes,
    load_state_order,
)

TUNE_ID = "3zn4c"
T_LENGTH = 100
ACCENT = "#9b111e"
BLUE = "#3b6fb6"
INK = "#1a1a1a"
BAND = {"maj7": "#f7f2f3", "min7": "#efe6e8", "dom7": "#f7f2f3",
        "m7b5": "#efe6e8", "dim7": "#f7f2f3"}

plt.rcParams.update({"font.family": "serif", "font.size": 9, "savefig.dpi": 300})


def quality_blocks(states) -> list[tuple[str, int, int]]:
    """(quality, first index, last index) for each contiguous quality block."""
    out, start = [], 0
    for i in range(1, len(states) + 1):
        if i == len(states) or states[i][1] != states[start][1]:
            out.append((states[start][1], start, i - 1))
            start = i
    return out


def panel(ax, seq, states, blocks, title, color) -> None:
    """Beat is the lowest-order digit of the canonical ordering, so each
    (quality, scale degree) group spans 8 consecutive indices and the beat
    coordinate is invisible as vertical position on a 428-tall axis.  It goes
    into the marker instead: filled = on an integer beat, hollow = offbeat."""
    for q, lo, hi in blocks:
        ax.add_patch(Rectangle((-2, lo - 0.5), T_LENGTH + 4, hi - lo + 1,
                               facecolor=BAND[q], edgecolor="none", zorder=0))
        ax.text(T_LENGTH + 1.5, (lo + hi) / 2, q, va="center", ha="left",
                fontsize=8, color=INK, style="italic")
    ax.plot(seq, color=color, linewidth=0.8, zorder=3)
    x = np.arange(len(seq))
    on = np.array([states[i][2] in STRONG_BEATS for i in seq])
    ax.scatter(x[on], np.array(seq)[on], s=13, color=color, zorder=4,
               label="on an integer beat")
    ax.scatter(x[~on], np.array(seq)[~on], s=13, facecolors="white",
               edgecolors=color, linewidths=0.8, zorder=4, label="offbeat")
    ax.set_xlim(-2, T_LENGTH + 2)
    ax.set_ylim(-0.5, len(states) - 0.5)
    ax.set_ylabel("state index")
    ax.set_title(title, fontsize=10, pad=6)
    ax.set_yticks([b[1] for b in blocks] + [len(states) - 1])
    ax.tick_params(axis="y", labelsize=7.5)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=2,
              handletextpad=0.3, columnspacing=1.0)


def main() -> None:
    states = load_state_order()
    index = {s: i for i, s in enumerate(states)}
    blocks = quality_blocks(states)

    df = load_notes()
    real = [index[s] for s in df[df.tune_id == TUNE_ID].state.tolist()[:T_LENGTH]]

    traj_path = DATA_DIR / "section9_plot_trajectory.npy"
    if not traj_path.exists():
        raise SystemExit(f"{traj_path} is missing -- run 09_generative_validation.py first.")
    synth = np.load(traj_path)[:T_LENGTH].tolist()

    fig, axes = plt.subplots(2, 1, figsize=(11.5, 4.0), sharex=True)
    panel(axes[0], real, states, blocks,
          f"Real: Anthropology, first {T_LENGTH} events (full state)", ACCENT)
    panel(axes[1], synth, states, blocks,
          f"Synthetic trajectory 1 (from P̂), first {T_LENGTH} events", BLUE)
    axes[-1].set_xlabel("event index")
    fig.tight_layout()

    out = FIGURES_DIR / "section_state_trajectory"
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)

    print(f"{len(states)} states; quality blocks: "
          + ", ".join(f"{q} [{lo}-{hi}]" for q, lo, hi in blocks))
    for name, seq in (("real", real), ("synthetic", synth)):
        on = sum(1 for i in seq if states[i][2] in STRONG_BEATS)
        print(f"{name:10} {len(set(seq)):3} distinct states in {T_LENGTH} events; "
              f"on-beat {on}, offbeat {len(seq) - on}")
    print(f"wrote {out}.png / .pdf")


if __name__ == "__main__":
    main()
