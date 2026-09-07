"""
Extract a per-event dataset (played notes + rests) from the Charlie Parker
Aligned Digital Omnibook.

For every event we record:
    tune_id, event_index, kind ('note'|'rest'), pitch_pc, chord_root_pc,
    chord_quality, scale_degree (int 0..11 for notes, the sentinel string
    REST_SD for rests), beat_position ('1'|'2'|'3'|'4'|'&1'..'&4'),
    chord_changed_from_prev, onset_midi_time, measure, state (the triple
    consumed by the Markov chain).

Why a custom extractor (instead of reusing PCSExtractor verbatim):
    The corpus encodes chord quality in <kind text="..."> with the element
    body set to "other".  music21's `cs.chordKind` therefore returns the
    literal string "other" and the existing IV pipeline silently dropped
    quality.  We recover quality by reading `cs.chordKindStr` (the `text`
    attribute) and fall back to a regex on `cs.figure` if needed.

Output: data/notes.parquet (now contains both notes and rests).

Run:
    python -m markov_chain.extract_notes
or
    python markov_chain/extract_notes.py
"""

from __future__ import annotations

import re
import sys
import warnings
from collections import Counter
from pathlib import Path

import pandas as pd
from music21 import converter, harmony, note as m21note, stream

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    BEAT_POSITIONS,
    DATA_DIR,
    NOTES_PARQUET,
    QUALITY_CLASSES,
    REST_SD,
    _serialize_state,
    classify_beat,
    map_kind_text,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
XML_DIR = REPO_ROOT / "xml"


# -----------------------------------------------------------------------------
# Chord-quality recovery
# -----------------------------------------------------------------------------

_FIGURE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(-7b5|m7b5|ø)", re.IGNORECASE), "m7b5"),
    (re.compile(r"dim", re.IGNORECASE), "dim7"),
    (re.compile(r"(?<![A-Z])maj7|M7|Δ", re.IGNORECASE), "maj7"),
    (re.compile(r"m(?!aj)"), "min7"),
    (re.compile(r"7"), "dom7"),
)


def quality_from_chord_symbol(cs: harmony.ChordSymbol) -> str | None:
    """Map a music21 ChordSymbol to one of QUALITY_CLASSES, or None if unmappable."""
    text = getattr(cs, "chordKindStr", None)
    if text is not None:
        q = map_kind_text(text)
        if q is not None:
            return q
    figure = cs.figure or ""
    body = re.sub(r"^[A-Ga-g][b#-]?", "", figure)
    if body == "":
        return "maj7"
    for pattern, quality in _FIGURE_PATTERNS:
        if pattern.search(body):
            return quality
    return None


# -----------------------------------------------------------------------------
# Per-tune extraction
# -----------------------------------------------------------------------------

def _build_chord_events(measures) -> list[dict]:
    """List of {global_offset, root_pc, quality, raw_text} sorted by offset."""
    events: list[dict] = []
    for m in measures:
        measure_offset = m.offset
        for cs in m.getElementsByClass(harmony.ChordSymbol):
            root = cs.root()
            if root is None:
                continue
            quality = quality_from_chord_symbol(cs)
            events.append(
                {
                    "global_offset": float(measure_offset + cs.offset),
                    "root_pc": int(root.pitchClass),
                    "quality": quality,
                    "raw_text": getattr(cs, "chordKindStr", None) or cs.figure,
                }
            )
    events.sort(key=lambda e: e["global_offset"])
    return events


def _build_event_stream(measures) -> list[dict]:
    """List of melodic events (notes + rests) sorted by global offset.

    Each event dict carries: kind ('note'|'rest'), global_offset, local_offset,
    measure, and (for notes) pitch_pc.  Tied notes collapse to onset (skip
    'stop'/'continue').  Rests are always emitted at their onset.
    """
    events: list[dict] = []
    for m in measures:
        measure_offset = m.offset
        for el in m.notesAndRests:
            global_offset = float(measure_offset + el.offset)
            local_offset = float(el.offset)
            measure_num = int(m.number) if m.number is not None else -1

            if isinstance(el, m21note.Note):
                if el.tie is not None and el.tie.type in ("stop", "continue"):
                    continue
                events.append({
                    "kind": "note",
                    "global_offset": global_offset,
                    "local_offset": local_offset,
                    "measure": measure_num,
                    "pitch_pc": int(el.pitch.pitchClass),
                })
            elif isinstance(el, m21note.Rest):
                events.append({
                    "kind": "rest",
                    "global_offset": global_offset,
                    "local_offset": local_offset,
                    "measure": measure_num,
                    "pitch_pc": -1,
                })
            # Chord (multi-note simultaneity) skipped — Parker's solos are single-line.
    events.sort(key=lambda e: e["global_offset"])

    # Collapse consecutive rests into a single event at the start of each silence
    # run.  A long silence (e.g., a multi-bar tacet) would otherwise produce one
    # rest event per quarter-beat where music21 emitted a Rest object, and the
    # resulting rest -> rest transitions would dominate the transition matrix
    # without conveying musical content.  Rule: keep the first rest in each
    # run, drop subsequent rests until the next Note appears.
    collapsed: list[dict] = []
    in_rest_run = False
    for ev in events:
        if ev["kind"] == "rest":
            if in_rest_run:
                continue
            in_rest_run = True
            collapsed.append(ev)
        else:
            in_rest_run = False
            collapsed.append(ev)
    return collapsed


def _active_chord_at(offset: float, chord_events: list[dict]) -> dict | None:
    """Return the most recent chord event with global_offset <= offset, or None."""
    active = None
    for ev in chord_events:
        if ev["global_offset"] <= offset + 1e-9:
            active = ev
        else:
            break
    return active


def extract_tune(xml_path: Path) -> tuple[list[dict], dict]:
    """Return (event rows, per-tune stats) for a single XML file."""
    tune_id = xml_path.stem
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        score = converter.parse(str(xml_path))

    if not isinstance(score, stream.Score) or not score.parts:
        return [], {"tune_id": tune_id, "error": f"unexpected top-level type {type(score).__name__}"}

    part = score.parts[0]
    measures = list(part.getElementsByClass("Measure"))
    chord_events = _build_chord_events(measures)
    raw_events = _build_event_stream(measures)

    rows: list[dict] = []
    prev_chord_key: tuple[int, str] | None = None
    skipped_no_chord = 0
    skipped_unmapped: Counter[str] = Counter()
    n_notes = 0
    n_rests = 0

    for ev in raw_events:
        active = _active_chord_at(ev["global_offset"], chord_events)
        if active is None:
            skipped_no_chord += 1
            continue
        if active["quality"] is None:
            skipped_unmapped[str(active["raw_text"])] += 1
            continue

        root_pc = active["root_pc"]
        quality = active["quality"]
        beat = classify_beat(ev["local_offset"])
        chord_key = (root_pc, quality)
        chord_changed = prev_chord_key is not None and chord_key != prev_chord_key

        if ev["kind"] == "note":
            scale_degree: int | str = (ev["pitch_pc"] - root_pc) % 12
            state = (int(scale_degree), quality, beat)
            n_notes += 1
        else:  # rest
            scale_degree = REST_SD
            state = (REST_SD, quality, beat)
            n_rests += 1

        rows.append({
            "tune_id": tune_id,
            "event_index": len(rows),
            "kind": ev["kind"],
            "pitch_pc": ev["pitch_pc"],
            "chord_root_pc": root_pc,
            "chord_quality": quality,
            "scale_degree": scale_degree,
            "beat_position": beat,
            "chord_changed_from_prev": bool(chord_changed),
            "onset_midi_time": ev["global_offset"],
            "measure": ev["measure"],
            "state": state,
        })
        prev_chord_key = chord_key

    stats = {
        "tune_id": tune_id,
        "n_events": len(rows),
        "n_notes": n_notes,
        "n_rests": n_rests,
        "n_chord_events": len(chord_events),
        "skipped_no_chord": skipped_no_chord,
        "skipped_unmapped": sum(skipped_unmapped.values()),
        "unmapped_breakdown": dict(skipped_unmapped),
    }
    return rows, stats


# -----------------------------------------------------------------------------
# Driver
# -----------------------------------------------------------------------------

def extract_corpus(xml_dir: Path = XML_DIR, limit: int | None = None) -> pd.DataFrame:
    xml_files = sorted(xml_dir.glob("*.xml"))
    if limit is not None:
        xml_files = xml_files[:limit]
    print(f"Found {len(xml_files)} XML files")

    all_rows: list[dict] = []
    all_stats: list[dict] = []
    quality_counter: Counter[str] = Counter()
    kind_counter: Counter[str] = Counter()
    beat_counter: Counter[str] = Counter()
    unmapped_counter: Counter[str] = Counter()

    for i, xml_path in enumerate(xml_files, 1):
        try:
            rows, stats = extract_tune(xml_path)
        except Exception as e:
            print(f"  [{i:>2}/{len(xml_files)}] {xml_path.name}: ERROR {e}")
            all_stats.append({"tune_id": xml_path.stem, "error": str(e)})
            continue
        all_rows.extend(rows)
        all_stats.append(stats)
        for r in rows:
            quality_counter[r["chord_quality"]] += 1
            kind_counter[r["kind"]] += 1
            beat_counter[r["beat_position"]] += 1
        for raw_text, n in stats.get("unmapped_breakdown", {}).items():
            unmapped_counter[raw_text] += n
        print(
            f"  [{i:>2}/{len(xml_files)}] {xml_path.name}: "
            f"notes={stats.get('n_notes', 0):>4d}  rests={stats.get('n_rests', 0):>3d}  "
            f"(chord events: {stats.get('n_chord_events', 0)})  "
            f"skipped: no-chord={stats.get('skipped_no_chord', 0)}, "
            f"unmapped-quality={stats.get('skipped_unmapped', 0)}"
        )

    df = pd.DataFrame(all_rows)

    print("\n=== Summary ===")
    print(f"Total events extracted: {len(df):,}  (notes={kind_counter['note']:,}, rests={kind_counter['rest']:,})")
    print(f"Total tunes processed : {len(all_stats)}")
    print(f"Quality distribution  : {dict(quality_counter)}")
    if unmapped_counter:
        print(f"Unmapped chord texts  : {dict(unmapped_counter)}")
    if not df.empty:
        theoretical = (12 + 1) * len(QUALITY_CLASSES) * len(BEAT_POSITIONS)  # 12 SDs + REST_SD
        print(f"Unique states observed: {df['state'].nunique()} / {theoretical} theoretical")
        for b in BEAT_POSITIONS:
            pct = 100 * beat_counter[b] / len(df)
            print(f"  beat-position '{b}'  : {beat_counter[b]:>5d} events ({pct:>4.1f}%)")
        chord_change_pct = df["chord_changed_from_prev"].mean() * 100
        print(f"Chord-change rate     : {chord_change_pct:.1f}% of events follow a chord change")
        per_tune = df.groupby("tune_id").size()
        print(f"Events per tune       : median={per_tune.median():.0f}, "
              f"min={per_tune.min()}, max={per_tune.max()}")

    return df


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = extract_corpus()
    df_to_save = df.copy()
    df_to_save["state"] = df_to_save["state"].apply(_serialize_state)
    # scale_degree is int-or-string (REST_SD) — cast to str so Parquet can store it.
    df_to_save["scale_degree"] = df_to_save["scale_degree"].astype(str)
    df_to_save.to_parquet(NOTES_PARQUET, index=False)
    print(f"\nWrote {NOTES_PARQUET}  ({len(df_to_save):,} rows)")


if __name__ == "__main__":
    main()
