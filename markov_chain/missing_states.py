"""
The 50 unobserved states.

275 of the 325 grid cells (13 scale degrees x 5 chord qualities x 5 beat
positions) occur in the corpus.  This script asks what the other 50 are, and
separates two very different reasons a cell can be empty:

    scarcity   m7b5 and dim7 carry ~165 events each and cannot cover 65 cells.
               Quantified against a null in which those events are drawn from
               the (degree, beat) profile of the well-sampled qualities.

    structure  a cell that is empty despite thousands of events on that chord
               quality.  Tested per cell with a Poisson tail: given how often
               the degree occurs on that quality at all, and the corpus-wide
               beat marginal, how surprising is a count of zero?

Writes data/missing_states_summary.json and figures/section_missing_states.*
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from math import exp
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    DATA_DIR,
    FIGURES_DIR,
    QUALITY_CLASSES,
    REST_SD,
    RNG_SEED,
    load_notes,
    scale_degree_name,
)

ACCENT = "#9b111e"
INK = "#1a1a1a"
MUTED = "#8c8c8c"
SOFT = "#f4e1e3"

plt.rcParams.update({"font.family": "serif", "font.size": 9, "savefig.dpi": 300})

BEATS = ["1", "2", "3", "4", "&1", "&2", "&3", "&4"]
DEGREES: list = list(range(12)) + [REST_SD]
WELL_SAMPLED = ("maj7", "min7", "dom7")
N_SIMS = 4000


def label(state) -> str:
    d, q, b = state
    beat = b if b.startswith("&") else f"♩{b}"
    return f"({scale_degree_name(d)}, {q}, {beat})"


def main() -> None:
    rng = np.random.default_rng(RNG_SEED)
    df = load_notes()
    states = list(df.state)
    observed = set(states)

    cells = [(d, b) for d in DEGREES for b in BEATS]
    grid = [(d, q, b) for d in DEGREES for q in QUALITY_CLASSES for b in BEATS]
    missing = [s for s in grid if s not in observed]

    # reference (degree, beat) profile from the well-sampled qualities
    ref = Counter((d, b) for d, q, b in states if q in WELL_SAMPLED)
    tot = sum(ref.values())
    probs = np.array([ref.get(c, 0) / tot for c in cells])

    beat_marg = Counter(b for _, _, b in states)
    beat_share = {b: beat_marg[b] / len(states) for b in BEATS}

    per_quality = []
    for q in QUALITY_CLASSES:
        n_q = sum(1 for _, qq, _ in states if qq == q)
        n_missing = sum(1 for _, qq, _ in missing if qq == q)
        covered = len(cells) - n_missing
        sims = np.array([
            len(set(rng.choice(len(cells), size=n_q, p=probs).tolist()))
            for _ in range(N_SIMS)
        ])
        per_quality.append({
            "quality": q,
            "events": n_q,
            "cells_covered": covered,
            "cells_total": len(cells),
            "cells_missing": n_missing,
            "null_coverage_mean": float(sims.mean()),
            "null_coverage_sd": float(sims.std()),
            "p_coverage_at_or_below": float((sims <= covered).mean()),
        })

    # structural zeros: empty cells on the well-sampled qualities
    structural = []
    for d, q, b in missing:
        if q not in WELL_SAMPLED:
            continue
        n_dq = sum(1 for dd, qq, _ in states if qq == q and dd == d)
        lam = n_dq * beat_share[b]
        breakdown = Counter(bb for dd, qq, bb in states if qq == q and dd == d)
        structural.append({
            "state": label((d, q, b)),
            "missing_cell": (d, q, b),
            "quality_events": sum(1 for _, qq, _ in states if qq == q),
            "degree_events_on_quality": n_dq,
            "beat_breakdown": {bb: breakdown.get(bb, 0) for bb in BEATS},
            "offbeat_share_pct": round(100 * sum(v for k, v in breakdown.items() if k.startswith("&")) / n_dq, 1),
            "expected_count": round(lam, 2),
            "poisson_p_zero": exp(-lam),
            "survives_bonferroni": exp(-lam) < 0.01 / len(grid),
            "bonferroni_threshold": 0.01 / len(grid),
        })
    structural.sort(key=lambda r: r["poisson_p_zero"])

    summary = {
        "grid_size": len(grid),
        "observed": len(observed),
        "missing": len(missing),
        "missing_on_rare_qualities": sum(1 for _, q, _ in missing if q not in WELL_SAMPLED),
        "corpus_offbeat_share_pct": round(100 * sum(v for k, v in beat_share.items() if k.startswith("&")), 1),
        "per_quality": per_quality,
        "structural_zeros": structural,
    }
    with (DATA_DIR / "missing_states_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    plot(per_quality, structural, beat_share, cells)

    print(f"{len(missing)} of {len(grid)} cells unobserved "
          f"({summary['missing_on_rare_qualities']} of them on m7b5 / dim7)")
    for row in per_quality:
        if row["cells_missing"]:
            print(f"  {row['quality']:6} {row['events']:6,} events  "
                  f"covers {row['cells_covered']}/{row['cells_total']}  "
                  f"null {row['null_coverage_mean']:.1f}±{row['null_coverage_sd']:.1f}  "
                  f"p={row['p_coverage_at_or_below']:.3f}")
    print("\nstructural zeros (empty despite a well-sampled quality):")
    for r in structural:
        print(f"  {r['state']:22} degree occurs {r['degree_events_on_quality']:3} times "
              f"({r['offbeat_share_pct']}% offbeat); expected {r['expected_count']}, "
              f"observed 0, P={r['poisson_p_zero']:.1e}"
              f"{'  [survives Bonferroni]' if r['survives_bonferroni'] else ''}")


def plot(per_quality, structural, beat_share, cells) -> None:
    fig, (ax_cov, ax_beat) = plt.subplots(1, 2, figsize=(10.0, 2.9), width_ratios=[1.0, 1.15])

    qs = [r["quality"] for r in per_quality]
    x = np.arange(len(qs))
    covered = [r["cells_covered"] for r in per_quality]
    null_mu = [r["null_coverage_mean"] for r in per_quality]
    null_sd = [r["null_coverage_sd"] for r in per_quality]

    ax_cov.bar(x, covered, width=0.6,
               color=[MUTED if q in WELL_SAMPLED else ACCENT for q in qs])
    ax_cov.errorbar(x, null_mu, yerr=null_sd, fmt="_", color=INK, markersize=14,
                    linewidth=1.0, capsize=3, label="expected under scarcity alone")
    ax_cov.set_xticks(x, qs)
    ax_cov.set_ylim(0, len(cells) * 1.08)
    ax_cov.set_ylabel(f"grid cells occupied (of {len(cells)})")
    ax_cov.set_title(f"Coverage of the {len(cells)}-cell grid, by chord quality", fontsize=10, pad=8)
    ax_cov.legend(frameon=False, fontsize=7.5, loc="upper right")
    ax_cov.spines[["top", "right"]].set_visible(False)
    ax_cov.tick_params(axis="x", length=0)

    # beat profile of the structural-zero degrees vs the corpus
    width = 0.26
    xb = np.arange(len(BEATS))
    ax_beat.bar(xb - width, [100 * beat_share[b] for b in BEATS], width=width,
                color=MUTED, label="all events")
    for i, r in enumerate(structural):
        vals = r["beat_breakdown"]
        n = sum(vals.values())
        d, q, _ = r["missing_cell"]
        ax_beat.bar(xb + i * width, [100 * vals[b] / n for b in BEATS], width=width,
                    color=ACCENT if i == 0 else SOFT, edgecolor=ACCENT, linewidth=0.8,
                    label=f"{scale_degree_name(d)} over {q}")
    ax_beat.set_xticks(xb, ["♩1", "♩2", "♩3", "♩4", "&1", "&2", "&3", "&4"])
    ax_beat.set_ylabel("% of that degree's events")
    ax_beat.set_title("Clash tones live offbeat, and skip one strong beat entirely",
                      fontsize=10, pad=8)
    ax_beat.legend(frameon=False, fontsize=7.5)
    ax_beat.spines[["top", "right"]].set_visible(False)
    ax_beat.tick_params(axis="x", length=0)

    fig.tight_layout()
    out = FIGURES_DIR / "section_missing_states"
    fig.savefig(out.with_suffix(".png"))
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


if __name__ == "__main__":
    main()
