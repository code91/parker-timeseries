"""
Section 12 — Is the on-beat / off-beat asymmetry directional?

The bebop scale is explicitly a *descending* device: a chromatic passing tone
is inserted so that a descending eighth-note line places chord tones on the
downbeats.  Ascending, the device does not work the same way.  The project's
research question already asks for the on-beat / off-beat asymmetry to be
recovered, but tests it undirected.  This section adds the direction.

Melodic direction is the sign of the interval between consecutive played
notes, measured on absolute pitch (extract_notes stores pitch_midi for this;
pitch class alone would misread the 8 % of intervals wider than a tritone).

This is a finding, not an operator: the claim is a contingency table, so no
decomposition of P is required to state it.

Writes data/section12_summary.json and figures/section12_direction.*
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    CHORD_TONES,
    DATA_DIR,
    FIGURES_DIR,
    REST_SD,
    STRONG_BEATS,
    load_notes,
)

ACCENT = "#9b111e"
MUTED = "#8c8c8c"
INK = "#1a1a1a"

plt.rcParams.update({"font.family": "serif", "font.size": 9, "savefig.dpi": 300})


def main() -> None:
    df = load_notes().sort_values(["tune_id", "event_index"]).reset_index(drop=True)
    st, midi, kind = df.state.values, df.pitch_midi.values, df.kind.values
    same_tune = df.tune_id.values == np.roll(df.tune_id.values, -1)

    ivs = Counter()
    land = {"down": [0, 0], "up": [0, 0]}          # [chord tones, total]
    for i in range(len(df) - 1):
        if not same_tune[i] or kind[i] != "note" or kind[i + 1] != "note":
            continue
        d = int(midi[i + 1]) - int(midi[i])
        ivs[d] += 1
        if d == 0:
            continue
        key = "down" if d < 0 else "up"
        dst = st[i + 1]
        if dst[2] not in STRONG_BEATS:
            continue
        land[key][1] += 1
        land[key][0] += dst[0] != REST_SD and dst[0] in CHORD_TONES[dst[1]]

    tot = sum(ivs.values())
    up = sum(v for k, v in ivs.items() if k > 0)
    down = sum(v for k, v in ivs.items() if k < 0)
    rep = ivs[0]
    step = sum(v for k, v in ivs.items() if 1 <= abs(k) <= 2)
    leap = tot - step - rep

    p_d = land["down"][0] / land["down"][1]
    p_u = land["up"][0] / land["up"][1]
    se = (p_d * (1 - p_d) / land["down"][1] + p_u * (1 - p_u) / land["up"][1]) ** 0.5
    z = (p_d - p_u) / se

    plot(ivs, land, p_d, p_u, FIGURES_DIR / "section12_direction")

    summary = {
        "intervals_total": tot,
        "up": up, "down": down, "repeat": rep,
        "down_to_up_ratio": down / up,
        "step_1_2_semitones": step, "leap_3_plus": leap,
        "chord_tone_on_strong_beat": {
            "down": {"hits": land["down"][0], "n": land["down"][1], "rate": p_d},
            "up": {"hits": land["up"][0], "n": land["up"][1], "rate": p_u},
            "difference_pp": 100 * (p_d - p_u), "se_pp": 100 * se, "z": z,
        },
    }
    with (DATA_DIR / "section12_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"note-to-note intervals : {tot:,}")
    print(f"  down {down:6,} ({100*down/tot:4.1f} %)   up {up:6,} ({100*up/tot:4.1f} %)"
          f"   repeat {rep:5,} ({100*rep/tot:4.1f} %)   down:up = {down/up:.2f}")
    print(f"  step (1-2 st) {step:6,} ({100*step/tot:4.1f} %)   leap (3+) {leap:6,} ({100*leap/tot:4.1f} %)")
    print("\nlanding on a strong beat, is it a chord tone?")
    print(f"  descending {land['down'][0]:5,}/{land['down'][1]:5,} = {100*p_d:.1f} %")
    print(f"  ascending  {land['up'][0]:5,}/{land['up'][1]:5,} = {100*p_u:.1f} %")
    print(f"  difference {100*(p_d-p_u):+.1f} pp   se {100*se:.1f}   z = {z:.1f}")
    print("Wrote section12_summary.json and figures")


def plot(ivs, land, p_d, p_u, out: Path) -> None:
    fig, (ax_iv, ax_rate) = plt.subplots(1, 2, figsize=(10.0, 3.4), width_ratios=[1.5, 1.0])

    ks = [k for k in range(-12, 13)]
    vals = [ivs.get(k, 0) for k in ks]
    tot = sum(ivs.values())
    colors = [ACCENT if k < 0 else MUTED if k > 0 else INK for k in ks]
    ax_iv.bar(ks, [100 * v / tot for v in vals], color=colors, width=0.78)
    ax_iv.set_xlabel("melodic interval (semitones, + = up)")
    ax_iv.set_ylabel("% of note-to-note moves")
    ax_iv.set_title("Bebop descends: crimson bars outweigh grey", fontsize=10, pad=8)
    ax_iv.spines[["top", "right"]].set_visible(False)

    bars = ax_rate.bar(["descending", "ascending"], [100 * p_d, 100 * p_u],
                       color=[ACCENT, MUTED], width=0.55)
    for b, v, n in zip(bars, (p_d, p_u), (land["down"][1], land["up"][1])):
        ax_rate.text(b.get_x() + b.get_width() / 2, 100 * v + 1.2, f"{100*v:.1f} %",
                     ha="center", fontsize=9, fontweight="bold")
        ax_rate.text(b.get_x() + b.get_width() / 2, 3, f"n = {n:,}", ha="center",
                     fontsize=7.5, color="white")
    ax_rate.set_ylim(0, 80)
    ax_rate.set_ylabel("lands on a chord tone")
    ax_rate.set_title("Landing on a strong beat", fontsize=10, pad=8)
    ax_rate.spines[["top", "right"]].set_visible(False)
    ax_rate.tick_params(axis="x", length=0)

    fig.tight_layout()
    fig.savefig(out.with_suffix(".png")); fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


if __name__ == "__main__":
    main()
