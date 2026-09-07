"""
Shared utilities for the Markov-chain analysis of Charlie Parker's bebop lines.

State space (v2)
----------------
Each state is a triple (scale_degree_or_rest, chord_quality, beat_position):
  - scale_degree_or_rest:
        int in {0, ..., 11}  for a played note (semitones above active chord root)
        the sentinel string  REST_SD  ("R") for a rest event
  - chord_quality:   one of QUALITY_CLASSES (5 classes)
  - beat_position:   one of BEAT_POSITIONS:
        "1", "2", "3", "4"  for notes/rests on a quarter-note grid position
                            within the bar (|offset mod 1| < BEAT_TOLERANCE)
        "&1", "&2", "&3", "&4"  otherwise (offbeat: swing eighths,
                            triplet and sixteenth positions), labelled by the
                            integer beat the event follows.  All 50 tunes are
                            4/4 with a single time signature, so the beat an
                            offbeat event follows is always well defined.

Total theoretical cardinality:
        played notes : 12 * 5 * 8 = 480
        rest events  :  1 * 5 * 8 =  40
        total        : 520.
Observed |S| is typically much smaller.

Canonical ordering
------------------
Sort key is (quality_index, is_rest, scale_degree_int, beat_index).  Within a
quality the played notes come first (sorted by scale-degree), then rests (one
per beat).  Beat order is 1 < 2 < 3 < 4 < &1 < &2 < &3 < &4 (so the offbeat
positions sort after all the integer beats).

Resolution set R
----------------
For the hitting-time analysis, R is the set of strong-beat chord-tone states:
        R = {(d, q, b) : d in CHORD_TONES[q],  b in {"1","2","3","4"}}.
i.e., any chord tone on any integer beat of the bar.  Rests are never in R.
Reaching R is interpreted as "harmonic resolution".

This module exposes the smoothing parameter, beat-position tolerance, RNG seed,
chord-quality mapping, chord-tone lookup, and a small set of IO helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence, Union

import numpy as np
import pandas as pd


# -----------------------------------------------------------------------------
# Tunable parameters (exposed at module level so each script can reference them)
# -----------------------------------------------------------------------------

# Laplace smoothing for transition-probability rows.  Small (0.01) so that
# observed transitions dominate, but undersampled rows do not produce NaNs
# in eigenvalue / hitting-time computations.
SMOOTHING_ALPHA: float = 0.01

# A note's onset is "on the grid" if its quarter-note offset within the measure
# satisfies |offset mod 1| < BEAT_TOLERANCE.  0.05 absorbs grace notes and
# transcriber rounding while keeping swing eighths in the offbeat class.
BEAT_TOLERANCE: float = 0.05

# Threshold below which a row of the count matrix is flagged as undersampled.
UNDERSAMPLED_ROW_THRESHOLD: int = 10

# Master RNG seed for every script.
RNG_SEED: int = 42


# -----------------------------------------------------------------------------
# Chord-quality classes
# -----------------------------------------------------------------------------

# 5 quality classes.  Order here defines the quality-index used in canonical
# state ordering, so do not reorder casually.
QUALITY_CLASSES: tuple[str, ...] = ("maj7", "min7", "dom7", "m7b5", "dim7")
QUALITY_INDEX: dict[str, int] = {q: i for i, q in enumerate(QUALITY_CLASSES)}

# Chord tones (scale degrees, in semitones above root) for each quality.
# These define which states belong to the resolution set R.
#   maj7  -> 1, 3, 5, 7
#   min7  -> 1, b3, 5, b7
#   dom7  -> 1, 3, 5, b7
#   m7b5  -> 1, b3, b5, b7
#   dim7  -> 1, b3, b5, bb7 (== 6)
CHORD_TONES: dict[str, frozenset[int]] = {
    "maj7": frozenset({0, 4, 7, 11}),
    "min7": frozenset({0, 3, 7, 10}),
    "dom7": frozenset({0, 4, 7, 10}),
    "m7b5": frozenset({0, 3, 6, 10}),
    "dim7": frozenset({0, 3, 6, 9}),
}

# Mapping from raw MusicXML <kind text="..."> attribute to one of QUALITY_CLASSES.
# Some entries map a triadic symbol to its seventh-chord extension as per bebop
# convention (bare "m" -> min7, blank -> maj7).  The single "6" instance is
# folded into maj7 (3 of 4 tones shared).  "/G" (1 instance, no quality info)
# and any unknown string are returned as None and excluded with a warning.
KIND_TEXT_MAP: dict[str, str] = {
    "7": "dom7",
    "m": "min7",
    "": "maj7",
    "dim": "dim7",
    "-7b5": "m7b5",
    "m7b5": "m7b5",
    "6": "maj7",
}


def map_kind_text(text: str | None) -> str | None:
    """Return the QUALITY_CLASSES entry for a <kind text="..."> string, or None."""
    if text is None:
        return None
    return KIND_TEXT_MAP.get(text)


# -----------------------------------------------------------------------------
# Beat positions (v2)
# -----------------------------------------------------------------------------

BEAT_POSITIONS: tuple[str, ...] = ("1", "2", "3", "4", "&1", "&2", "&3", "&4")
BEAT_INDEX: dict[str, int] = {b: i for i, b in enumerate(BEAT_POSITIONS)}
STRONG_BEATS: frozenset[str] = frozenset({"1", "2", "3", "4"})


def classify_beat(local_offset_quarters: float) -> str:
    """Return one of BEAT_POSITIONS for an offset within a measure (quarter-note units).

    Integer beats within tolerance return the corresponding beat label ('1',
    '2', '3', '4').  Anything else is offbeat and is labelled by the beat
    it follows: '&1' for the space after beat 1, and so on.  This distinguishes
    the pickup position ('&4', immediately before the next bar and, usually,
    the next chord) from mid-bar off-beats, which the earlier single '&' class
    could not express.

    Beats outside 1-4 (e.g. beat 5 in 5/4) clamp to the 4 / '&4' class to keep
    the state space bounded.  No event in this corpus needs the clamp: all 50
    tunes are 4/4 and every local offset falls in [0, 4).
    """
    frac = local_offset_quarters - round(local_offset_quarters)
    if abs(frac) < BEAT_TOLERANCE:
        beat_number = int(round(local_offset_quarters)) + 1  # 1-indexed
        return str(beat_number) if 1 <= beat_number <= 4 else "4"
    beat_number = int(local_offset_quarters // 1) + 1
    return f"&{beat_number}" if 1 <= beat_number <= 4 else "&4"


# -----------------------------------------------------------------------------
# Scale-degree pretty-printing
# -----------------------------------------------------------------------------

SCALE_DEGREE_NAMES: tuple[str, ...] = (
    "1", "b2", "2", "b3", "3", "4", "#4", "5", "b6", "6", "b7", "7",
)

REST_SD: str = "R"  # sentinel value for the scale-degree slot of a rest event


def scale_degree_name(d: Union[int, str]) -> str:
    """Human-readable scale degree, e.g. 10 -> 'b7'.  REST_SD -> 'rest'."""
    if d == REST_SD:
        return "rest"
    assert isinstance(d, int)
    return SCALE_DEGREE_NAMES[d % 12]


# -----------------------------------------------------------------------------
# State construction, ordering, and lookup
# -----------------------------------------------------------------------------

# First slot is int (0..11) for a played note, or REST_SD for a rest.
State = tuple[Union[int, str], str, str]


def is_rest_state(s: State) -> bool:
    return s[0] == REST_SD


def make_state(scale_degree: Union[int, str], chord_quality: str, beat_position: str) -> State:
    assert scale_degree == REST_SD or (isinstance(scale_degree, int) and 0 <= scale_degree < 12)
    assert chord_quality in QUALITY_INDEX, f"unknown quality {chord_quality}"
    assert beat_position in BEAT_INDEX, f"unknown beat {beat_position}"
    return (scale_degree, chord_quality, beat_position)


def state_sort_key(s: State) -> tuple[int, int, int, int]:
    """(quality_index, is_rest, scale_degree_int, beat_index)."""
    d, q, b = s
    is_rest = 1 if d == REST_SD else 0
    sd_int = 0 if d == REST_SD else int(d)  # type: ignore[arg-type]
    return (QUALITY_INDEX[q], is_rest, sd_int, BEAT_INDEX[b])


def canonical_state_order(observed: Iterable[State]) -> list[State]:
    """Sort an iterable of observed states into the canonical row/column order."""
    return sorted(set(observed), key=state_sort_key)


def state_index_map(states: Sequence[State]) -> dict[State, int]:
    return {s: i for i, s in enumerate(states)}


def state_label(s: State) -> str:
    """Compact string label, e.g. (b7, dom7, ♩1) or (rest, dom7, &).

    The beat-position is prefixed with a quarter-note glyph for strong beats
    (so 'beat 1' renders as '♩1', not bare '1') because scale-degree names
    are also short integer-like strings ('1', '2', '3', '4') and the two
    slots would otherwise be visually ambiguous.  Offbeat '&N' stays bare.
    """
    d, q, b = s
    b_pretty = b if b.startswith("&") else f"♩{b}"
    return f"({scale_degree_name(d)}, {q}, {b_pretty})"


# -----------------------------------------------------------------------------
# Resolution set R
# -----------------------------------------------------------------------------

def is_chord_tone_state(s: State) -> bool:
    """A state is in R iff it is a played note on a strong beat (1-4)
    whose scale degree is a chord tone of the active quality.

    Rests are never in R."""
    d, q, b = s
    if d == REST_SD:
        return False
    return b in STRONG_BEATS and d in CHORD_TONES[q]


def resolution_indices(states: Sequence[State]) -> np.ndarray:
    """Indices (into `states`) of the resolution-set members."""
    return np.array(
        [i for i, s in enumerate(states) if is_chord_tone_state(s)],
        dtype=np.int64,
    )


# -----------------------------------------------------------------------------
# IO helpers
# -----------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
FIGURES_DIR = REPO_ROOT / "figures"
NOTES_PARQUET = DATA_DIR / "notes.parquet"


def _serialize_state(s: State) -> str:
    """Pipe-delimited form for Parquet storage."""
    return f"{s[0]}|{s[1]}|{s[2]}"


def _parse_state(s: str) -> State:
    d_str, q, b = s.split("|")
    d: Union[int, str] = REST_SD if d_str == REST_SD else int(d_str)
    return (d, q, b)


def load_notes() -> pd.DataFrame:
    """Load the per-note dataset produced by extract_notes.py.

    Re-hydrates the `state` column from its pipe-delimited Parquet form
    back into Python tuples (scale_degree_or_REST_SD, chord_quality, beat_position).
    """
    df = pd.read_parquet(NOTES_PARQUET)
    if "state" in df.columns and df["state"].dtype == object and len(df):
        first = df["state"].iloc[0]
        if isinstance(first, str) and "|" in first:
            df["state"] = df["state"].apply(_parse_state)
    return df


def operator_path(name: str) -> Path:
    return DATA_DIR / f"{name}.npy"


def save_operator(name: str, P: np.ndarray) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    np.save(operator_path(name), P)


def load_operator(name: str) -> np.ndarray:
    return np.load(operator_path(name))


STATES_PATH = DATA_DIR / "states.json"


def save_state_order(states: Sequence[State]) -> None:
    """Persist the canonical state ordering so every analysis script reads the same indices."""
    import json
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = [{"scale_degree": d, "chord_quality": q, "beat_position": b} for (d, q, b) in states]
    with STATES_PATH.open("w") as f:
        json.dump(payload, f, indent=2)


def load_state_order() -> list[State]:
    import json
    with STATES_PATH.open() as f:
        payload = json.load(f)
    return [(row["scale_degree"], row["chord_quality"], row["beat_position"]) for row in payload]
