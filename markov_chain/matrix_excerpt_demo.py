"""
The operator shown as what it is: a 428 x 428 grid of numbers.

Left  the whole of P-hat as a log-heatmap, with the excerpt boxed in.
Right a contiguous 12 x 12 block of it with every probability printed to two
      decimals, so "428 rows of a table" stops being an abstraction.  Two
      decimals rather than a "< 0.5 %" symbol: the cells below that threshold
      still span a 100x range, which the colour shows and a single symbol hid.

The block is contiguous on purpose.  A submatrix hand-picked from the busiest
cells would look dense and would misrepresent an operator that is 97 % zeros.

Standalone: run after 01_transition_matrices.py.
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
    REST_SD,
    FIGURES_DIR,
    load_operator,
    load_state_order,
    scale_degree_name,
)

ACCENT = "#9b111e"
CMAP = "RdPu"
INK = "#1a1a1a"
ROW0, COL0, SPAN = 282, 264, 12
HIGHLIGHT = (10, "dom7", "&4")

plt.rcParams.update({"font.family": "serif", "font.size": 9, "savefig.dpi": 300})


def label(s) -> str:
    """Show the semitone and the musician's name together, e.g. "10 (b7)".
    The slides define d as (pc_note - pc_root) mod 12, so the number has to be
    visible; the name is what makes the row readable as music."""
    d, q, b = s
    deg = REST_SD if d == REST_SD else f"{d} ({scale_degree_name(d)})"
    return f"{deg}, {q}, {b if b.startswith('&') else '♩' + b}"


def main() -> None:
    states = load_state_order()
    P = load_operator("P")
    n = len(states)
    hi_row = states.index(HIGHLIGHT)

    fig, (ax_full, ax_zoom) = plt.subplots(1, 2, figsize=(11.0, 4.6),
                                           width_ratios=[1.0, 1.35])

    # --- the whole operator -------------------------------------------------
    ax_full.imshow(np.log10(P), cmap=CMAP, aspect="equal", interpolation="nearest")
    ax_full.add_patch(Rectangle((COL0 - 0.5, ROW0 - 0.5), SPAN, SPAN,
                                fill=False, edgecolor=ACCENT, linewidth=1.4))
    ax_full.set_title(f"$\\hat{{P}}$, all {n} × {n} cells (log scale)", fontsize=10, pad=8)
    ax_full.set_xlabel("to state"); ax_full.set_ylabel("from state")
    ax_full.tick_params(labelsize=7.5)

    # --- a contiguous block, with the numbers -------------------------------
    blk = P[ROW0:ROW0 + SPAN, COL0:COL0 + SPAN]
    ax_zoom.imshow(np.log10(blk), cmap=CMAP, aspect="equal",
                   interpolation="nearest",
                   vmin=np.log10(P).min(), vmax=np.log10(P).max())
    for r in range(SPAN):
        for c in range(SPAN):
            v = blk[r, c] * 100
            ax_zoom.text(c, r, f"{v:.2f}", ha="center", va="center", fontsize=5.8,
                         color="white" if v > 8 else INK)
    ax_zoom.set_xticks(range(SPAN), [label(states[COL0 + c]) for c in range(SPAN)],
                       rotation=90, fontsize=6.5)
    ax_zoom.set_yticks(range(SPAN), [label(states[ROW0 + r]) for r in range(SPAN)],
                       fontsize=6.5)
    for lbl in ax_zoom.get_yticklabels():
        if lbl.get_text() == label(HIGHLIGHT):
            lbl.set_color(ACCENT); lbl.set_fontweight("bold")
    ax_zoom.add_patch(Rectangle((-0.5, hi_row - ROW0 - 0.5), SPAN, 1,
                                fill=False, edgecolor=ACCENT, linewidth=1.4))
    ax_zoom.set_title("the boxed block, as percentages", fontsize=10, pad=8)
    # rows sum to 1 over all 428 columns, not over the 12 shown here
    ax_zoom.set_xlabel(f"to state  ({SPAN} of {n} columns)", fontsize=8)
    ax_zoom.set_ylabel(f"from state  ({SPAN} of {n} rows)", fontsize=8)

    fig.tight_layout()
    out = FIGURES_DIR / "section_matrix_excerpt"
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)

    print(f"block rows {ROW0}-{ROW0 + SPAN - 1}, cols {COL0}-{COL0 + SPAN - 1}")
    print(f"highlighted row {hi_row}: {label(states[hi_row])}")
    print(f"wrote {out}.png / .pdf")


if __name__ == "__main__":
    main()
