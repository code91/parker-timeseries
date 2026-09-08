"""
One-off figure for the corpus slide: the two descriptive distributions worth
looking at rather than reading as a list of numbers.

    left   beat-position distribution over all 23,143 events.  The headline is
           the offbeat classes (&1..&4) together take 55 % of events, and
           each individually outweighs no single downbeat by much -- but the
           on/off asymmetry is what the whole project is built to measure.
    right  events per tune across the 50 solos, with the median marked.

Numbers come from data/notes.parquet via common.load_notes(), so the figure
cannot drift from the corpus it describes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import FIGURES_DIR, load_notes  # noqa: E402

ACCENT = "#9b111e"
INK = "#1a1a1a"
MUTED = "#8c8c8c"
SOFT = "#f4e1e3"

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "savefig.dpi": 300,
})

BEAT_ORDER = ["1", "2", "3", "4", "&1", "&2", "&3", "&4"]
BEAT_LABELS = ["♩1", "♩2", "♩3", "♩4", "&1", "&2", "&3", "&4"]


def main() -> None:
    df = load_notes()

    fig, (ax_beat, ax_len) = plt.subplots(1, 2, figsize=(10.0, 2.5), width_ratios=[1.15, 1.0])

    # --- beat position ------------------------------------------------------
    share = df.beat_position.value_counts(normalize=True).mul(100).reindex(BEAT_ORDER)
    colors = [MUTED] * 4 + [ACCENT] * 4
    bars = ax_beat.bar(BEAT_LABELS, share.values, color=colors, width=0.62)
    for b, v in zip(bars, share.values):
        ax_beat.text(b.get_x() + b.get_width() / 2, v + 0.4, f"{v:.1f} %",
                     ha="center", va="bottom", fontsize=8.5,
                     color=ACCENT if b.get_x() > 3.5 else INK,
                     fontweight="bold" if b.get_x() > 3.5 else "normal")
    # the four offbeat classes only read as an asymmetry when totalled
    off = float(share[[b for b in BEAT_ORDER if b.startswith("&")]].sum())
    ax_beat.plot([3.62, 7.38], [17.6, 17.6], color=ACCENT, linewidth=0.9)
    for xt in (3.62, 7.38):
        ax_beat.plot([xt, xt], [17.0, 17.6], color=ACCENT, linewidth=0.9)
    ax_beat.text(5.5, 18.1, f"offbeat: {off:.1f} % combined", ha="center",
                 fontsize=8.5, color=ACCENT, fontweight="bold")
    ax_beat.set_ylim(0, 21)
    ax_beat.set_ylabel("share of events")
    ax_beat.set_title("Where events fall in the bar", fontsize=10, pad=8)
    ax_beat.spines[["top", "right"]].set_visible(False)
    ax_beat.tick_params(axis="x", length=0)

    # --- events per tune ----------------------------------------------------
    per_tune = df.groupby("tune_id").size().values
    median = float(np.median(per_tune))
    ax_len.hist(per_tune, bins=12, color=SOFT, edgecolor=ACCENT, linewidth=0.9)
    ax_len.axvline(median, color=INK, linestyle="--", linewidth=1.0)
    ax_len.text(0.97, 0.90, f"median {median:.0f}", transform=ax_len.transAxes,
                ha="right", va="top", fontsize=8.5, color=INK)
    ax_len.set_xlabel("events per tune")
    ax_len.set_ylabel("number of tunes")
    ax_len.set_title(f"Solo length across the {len(per_tune)} tunes", fontsize=10, pad=8)
    ax_len.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = FIGURES_DIR / "section_corpus_stats"
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)

    print(f"beat shares: {dict(share.round(2))}")
    print(f"events per tune: median {median:.0f}, range {per_tune.min()}-{per_tune.max()}")
    print(f"wrote {out}.png / .pdf")


if __name__ == "__main__":
    main()
