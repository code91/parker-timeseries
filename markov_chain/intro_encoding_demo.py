"""
One-off figure for the framing slide: show how the first ~8 notes of
Anthropology (tune id 3zn4c) get encoded into the (scale_degree,
chord_quality, beat_position) state space.

Pulls notes via the existing extractor so the data is authoritative.
Renders four stacked rows:

    chord     — bracket spanning the notes under each active chord
    pitch     — letter name of each played note
    arrow     — visual abstraction step
    state     — composed tuple (scale_degree, quality, beat_position)
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import FIGURES_DIR, REST_SD, SCALE_DEGREE_NAMES  # noqa: E402
from markov_chain.extract_notes import extract_tune  # noqa: E402

PC_NAMES = ("C", "D♭", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B")
ACCENT = "#9b111e"
INK = "#1a1a1a"
MUTED = "#6b6b6b"
SOFT = "#f4e1e3"

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "savefig.dpi": 300,
})


def chord_label(root_pc: int, quality: str) -> str:
    suffix = {
        "maj7": "maj7",
        "min7": "m7",
        "dom7": "7",
        "m7b5": "m7♭5",
        "dim7": "°7",
    }[quality]
    return f"{PC_NAMES[root_pc]}{suffix}"


def main() -> None:
    xml_path = Path(__file__).resolve().parent.parent / "xml" / "3zn4c.xml"
    rows, _ = extract_tune(xml_path)
    # v2: events may include rest events.  Take 10 to capture the leading rest
    # of the pickup measure plus the same 9-note phrase that the v1 demo showed.
    events = rows[:10]
    if not events:
        raise RuntimeError("no notes extracted for 3zn4c")

    n = len(events)
    fig, ax = plt.subplots(figsize=(14.0, 4.6))

    # Vertical layout — y values for each row
    Y_CHORD = 4.4
    Y_PITCH = 3.2
    Y_ARROW = 2.4
    Y_STATE = 1.3

    # ---- Chord brackets ----
    # Group consecutive notes sharing (root_pc, quality)
    segments = []  # list of (start_idx, end_idx, label)
    cur_key = None
    cur_start = 0
    for i, e in enumerate(events):
        key = (e["chord_root_pc"], e["chord_quality"])
        if key != cur_key:
            if cur_key is not None:
                segments.append((cur_start, i - 1, chord_label(*cur_key)))
            cur_key = key
            cur_start = i
    segments.append((cur_start, n - 1, chord_label(*cur_key)))

    for start, end, label in segments:
        x0, x1 = start - 0.4, end + 0.4
        ax.plot([x0, x0, x1, x1], [Y_CHORD - 0.15, Y_CHORD + 0.05, Y_CHORD + 0.05, Y_CHORD - 0.15],
                color=ACCENT, linewidth=1.2)
        ax.text((x0 + x1) / 2, Y_CHORD + 0.32, label,
                ha="center", va="bottom",
                fontsize=14, fontweight="bold", color=ACCENT)

    # ---- Pitch row: note letter (or rest glyph) inside a rounded box ----
    for i, e in enumerate(events):
        is_rest = e["scale_degree"] == REST_SD
        if is_rest:
            name = "rest"
            face = "#f0f0f0"
            txt_color = MUTED
            txt_size = 12
        else:
            name = PC_NAMES[e["pitch_pc"]]
            face = "white"
            txt_color = INK
            txt_size = 15
        box = FancyBboxPatch(
            (i - 0.32, Y_PITCH - 0.32), 0.64, 0.64,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            linewidth=1.0, edgecolor=INK, facecolor=face,
        )
        ax.add_patch(box)
        ax.text(i, Y_PITCH, name, ha="center", va="center",
                fontsize=txt_size, fontweight="bold", color=txt_color)

    # ---- Arrow row ----
    for i in range(n):
        ax.annotate(
            "", xy=(i, Y_ARROW - 0.35), xytext=(i, Y_ARROW + 0.35),
            arrowprops=dict(arrowstyle="->", color=MUTED, linewidth=1.0),
        )
    ax.text(-0.9, Y_ARROW, "encode", ha="right", va="center",
            fontsize=11, style="italic", color=MUTED)

    # ---- State row: composed tuple in a soft pill ----
    for i, e in enumerate(events):
        if e["scale_degree"] == REST_SD:
            sd_name = "rest"
        else:
            sd_name = SCALE_DEGREE_NAMES[e["scale_degree"]]
        b_pretty = e["beat_position"] if e["beat_position"].startswith("&") else f"♩{e['beat_position']}"
        text = f"({sd_name}, {e['chord_quality']}, {b_pretty})"
        box = FancyBboxPatch(
            (i - 0.44, Y_STATE - 0.30), 0.88, 0.60,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            linewidth=0.8, edgecolor=ACCENT, facecolor=SOFT,
        )
        ax.add_patch(box)
        ax.text(i, Y_STATE, text, ha="center", va="center",
                fontsize=9.5, color=INK, fontfamily="monospace")

    # ---- Row labels (left side) ----
    label_x = -0.9
    ax.text(label_x, Y_CHORD + 0.32, "chord", ha="right", va="bottom",
            fontsize=11, style="italic", color=MUTED)
    ax.text(label_x, Y_PITCH, "note", ha="right", va="center",
            fontsize=11, style="italic", color=MUTED)
    ax.text(label_x, Y_STATE, "state", ha="right", va="center",
            fontsize=11, style="italic", color=MUTED)

    # Mark chord-change positions with a faint vertical line
    for start, _, _ in segments[1:]:
        ax.axvline(start - 0.5, color=ACCENT, linestyle=":", linewidth=0.8, alpha=0.55)

    ax.set_xlim(-1.45, n - 0.3)  # just clears the right-aligned row labels
    ax.set_ylim(0.5, 5.2)
    ax.axis("off")

    fig.suptitle(
        "From melody to state space: pickup-measure rest + first 9 notes of $\\it{Anthropology}$ (Parker)",
        fontsize=13, y=0.99,
    )
    fig.tight_layout()
    out = FIGURES_DIR / "section_intro_encoding"
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)
    print(f"Wrote {out}.png and .pdf")


if __name__ == "__main__":
    main()
