"""
One-off figure for the corpus slide: four bars of Anthropology (tune id
3zn4c) as Parker played them, above a line of the same length sampled from
the fitted operator P̂ and engraved as real notation.

Both staves are rendered by music21 -> MuseScore over the identical changes,
so the comparison is like-for-like.

Two things the state space does not carry have to be supplied to turn a
state sequence back into notation:

    harmony  — the chain emits scale degrees, not pitches.  The synthetic
               line is realized over Anthropology's own changes.
    octave   — not modelled.  Nearest-neighbour voice leading from the
               previous note, clamped to the real excerpt's register shifted
               up by SYNTH_OCTAVE_SHIFT.  The excerpt sits at A3-F4, which
               engraves with ledger lines below the treble staff; an octave up
               is A4-F5, which sits inside it.  Octave carries no meaning in
               the state space, so this costs nothing.

Duration is not modelled either, so the sampled line is laid out as a plain
eighth-note stream (the bebop default, and what the corpus overwhelmingly
is).  Beat position therefore does not drive the rhythm here; instead we
report how often the generated beat token agrees with the eighth-grid slot
it landed on, which is the honest way to show that dimension in a figure
that has to fix the rhythm.

Chord symbols are rebuilt from the extracted data rather than reused from
the MusicXML: music21's cs.chordKind returns the literal "other" for this
corpus (see CLAUDE.md), so the source ChordSymbol objects engrave wrongly.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from music21 import (clef, converter, expressions, harmony, key, metadata, meter,
                     note, stream, tempo)

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    DATA_DIR,
    classify_beat,
    FIGURES_DIR,
    REST_SD,
    RNG_SEED,
    load_notes,
    load_state_order,
)

TUNE_ID = "3zn4c"
FIRST_MEASURE = 1
LAST_MEASURE = 5
XML_DIR = Path(__file__).resolve().parent.parent / "xml"
TRAJECTORY_PATH = DATA_DIR / "section9_plot_trajectory.npy"
# Parker's line is a pickup into bar 2; the sampled staff enters on that
# downbeat rather than filling the pickup bar, so the two lines start together.
SYNTH_START_BAR = 1
SYNTH_OCTAVE_SHIFT = 12
# Duration is not modelled, so a rest has no length of its own.  Rather than
# engrave every rest as an eighth, draw one at random from REST_DURATIONS.  A
# rest longer than an eighth absorbs the events on the slots it covers, so the
# staff shows slightly fewer events than the walk emitted.  Seeded, so the
# figure is reproducible.
REST_DURATIONS: tuple[float, ...] = (0.5, 1.0, 1.5)
# Parker's staff is engraved at written pitch.  Octave carries no meaning in
# the state space, so this is purely a display choice; set to 12 to lift it
# into the same register as the sampled staff below.
REAL_OCTAVE_SHIFT = 0

QUALITY_SUFFIX = {"maj7": "maj7", "min7": "m7", "dom7": "7", "m7b5": "m7\u266d5", "dim7": "dim7"}
PC_SPELLING = ("C", "D\u266d", "D", "E\u266d", "E", "F", "G\u266d", "G", "A\u266d", "A", "B\u266d", "B")


# MuseScore 4 drops <root> when importing a MusicXML <harmony> and engraves the
# kind alone ("maj7" instead of "B♭maj7"), whatever the encoding.  Staff text
# sidesteps the importer and gives exact control over the spelling.
def chord_symbol(root_pc: int, quality: str) -> expressions.TextExpression:
    te = expressions.TextExpression(f"{PC_SPELLING[root_pc % 12]}{QUALITY_SUFFIX[quality]}")
    te.placement = "above"
    te.style.fontWeight = "bold"
    te.style.fontSize = 10
    return te


def autocrop(path: Path, pad: int = 24, max_gap: int = 46) -> None:
    """Trim the page margins, then squeeze the vertical white band MuseScore
    leaves between systems down to max_gap, so a two-system excerpt does not
    arrive with a third of its height empty."""
    img = Image.open(path).convert("RGB")
    mask = img.convert("L").point(lambda v: 255 if v < 240 else 0)
    box = mask.getbbox()
    if box is None:
        return
    l, t, r, b = box
    img = img.crop((max(0, l - pad), max(0, t - pad),
                    min(img.width, r + pad), min(img.height, b + pad)))

    ink = np.array(img.convert("L")) < 240
    rows = ink.any(axis=1)
    keep, run = [], 0
    for y, has_ink in enumerate(rows):
        if has_ink:
            run = 0
            keep.append(y)
        else:
            run += 1
            if run <= max_gap:
                keep.append(y)
    if len(keep) < len(rows):
        img = Image.fromarray(np.array(img)[keep])
    img.save(path)


# MuseScore 4 ignores -S when rendering MusicXML straight to an image, and it
# ignores <defaults><page-layout> in the MusicXML too.  It *does* apply the
# style when converting MusicXML to .mscz, so the render is two steps: convert
# with a wide page, then rasterise the .mscz.  That keeps all five measures on
# one system instead of wrapping onto a second.  10 inches is the
# narrowest page that still holds all five; 9 wraps.
MSCORE = Path("/Applications/MuseScore 4.app/Contents/MacOS/mscore")

STYLE = """<?xml version="1.0" encoding="UTF-8"?>
<museScore version="4.00">
  <Style>
    <pageWidth>10</pageWidth>
    <pageHeight>5.2</pageHeight>
    <pagePrintableWidth>9.6</pagePrintableWidth>
    <pageEvenLeftMargin>0.2</pageEvenLeftMargin>
    <pageOddLeftMargin>0.2</pageOddLeftMargin>
    <pageEvenTopMargin>0.2</pageEvenTopMargin>
    <pageOddTopMargin>0.2</pageOddTopMargin>
    <pageEvenBottomMargin>0.2</pageEvenBottomMargin>
    <pageOddBottomMargin>0.2</pageOddBottomMargin>
    <spatium>2.2</spatium>
  </Style>
</museScore>
"""


def render(score: stream.Score, out: Path) -> None:
    tmp = out.parent / "_notation_tmp"
    xml_path = Path(str(score.write("musicxml", fp=str(tmp.with_suffix(".musicxml")))))
    style_path = tmp.with_suffix(".mss")
    style_path.write_text(STYLE)
    mscz = tmp.with_suffix(".mscz")
    subprocess.run([str(MSCORE), "-S", str(style_path), "-o", str(mscz), str(xml_path)],
                   check=True, capture_output=True)
    subprocess.run([str(MSCORE), "-r", "300", "-o", str(out), str(mscz)],
                   check=True, capture_output=True)
    produced = sorted(out.parent.glob(f"{out.stem}-*.png"))
    if produced:
        produced[0].replace(out)
        for stray in produced[1:]:
            stray.unlink()
    subprocess.run([str(MSCORE), "-o", str(out.with_suffix(".pdf")), str(mscz)],
                   check=True, capture_output=True)
    for f in (xml_path, style_path, mscz):
        f.unlink(missing_ok=True)
    autocrop(out)


def main() -> None:
    df = load_notes()
    tune = df[df.tune_id == TUNE_ID].sort_values("event_index")
    window = tune[(tune.measure >= FIRST_MEASURE) & (tune.measure <= LAST_MEASURE)]
    start_offset = float(window.onset_midi_time.min())
    n_bars = LAST_MEASURE - FIRST_MEASURE + 1
    synth_lead_in = 4.0 * SYNTH_START_BAR
    n_slots = (n_bars - SYNTH_START_BAR) * 8

    changes = tune[["onset_midi_time", "chord_root_pc", "chord_quality"]].values

    def chord_at(abs_offset: float) -> tuple[int, str]:
        active = [c for c in changes if c[0] <= abs_offset + 1e-9]
        row = active[-1] if active else changes[0]
        return int(row[1]), str(row[2])

    # --- real staff, from the source MusicXML --------------------------------
    src = converter.parse(XML_DIR / f"{TUNE_ID}.xml")
    real = src.parts[0].measures(FIRST_MEASURE, LAST_MEASURE)
    real_pitches = [n.pitch.midi for n in real.recurse().notes if hasattr(n, "pitch")]
    lo = min(real_pitches) + SYNTH_OCTAVE_SHIFT
    hi = max(real_pitches) + SYNTH_OCTAVE_SHIFT
    # after the register above is fixed, so both staves land in the same octave
    real.transpose(REAL_OCTAVE_SHIFT, inPlace=True)

    for cs in list(real.recurse().getElementsByClass(harmony.ChordSymbol)):
        cs.activeSite.remove(cs)
    # the pickup measure carries the Omnibook's tempo mark; irrelevant here
    for mm in list(real.recurse().getElementsByClass(tempo.MetronomeMark)):
        mm.activeSite.remove(mm)

    ks = real.recurse().getElementsByClass(key.KeySignature)
    sharps = ks[0].sharps if ks else 0

    # --- synthetic staff -----------------------------------------------------
    states = load_state_order()
    if not TRAJECTORY_PATH.exists():
        raise SystemExit(
            f"{TRAJECTORY_PATH} is missing -- run 09_generative_validation.py first."
        )
    seq = np.load(TRAJECTORY_PATH)[:n_slots].tolist()

    synth = stream.Part()
    synth.insert(0, clef.TrebleClef())
    synth.insert(0, key.KeySignature(sharps))
    synth.insert(0, meter.TimeSignature("4/4"))

    if synth_lead_in:
        synth.insert(0.0, note.Rest(quarterLength=synth_lead_in))

    prev_midi = real_pitches[0] + SYNTH_OCTAVE_SHIFT
    beat_agreements = 0
    rng = np.random.default_rng(RNG_SEED)
    skip_until = -1.0
    for k, si in enumerate(seq):
        rel = synth_lead_in + 0.5 * k
        if rel < skip_until:
            continue
        sd, _q, beat = states[si]
        slot_beat = classify_beat(rel % 4.0)
        beat_agreements += int(slot_beat == beat)
        if sd == REST_SD:
            dur = float(rng.choice(REST_DURATIONS))
            dur = min(dur, start_offset + 4.0 * n_bars - (start_offset + rel))
            synth.insert(rel, note.Rest(quarterLength=dur))
            skip_until = rel + dur
            continue
        root_pc, _ = chord_at(start_offset + rel)
        target_pc = (root_pc + int(sd)) % 12
        cands = [target_pc + 12 * o for o in range(11) if lo <= target_pc + 12 * o <= hi]
        if not cands:
            cands = [target_pc + 12 * round((prev_midi - target_pc) / 12)]
        midi = min(cands, key=lambda m: (abs(m - prev_midi), m))
        prev_midi = midi
        synth.insert(rel, note.Note(midi, quarterLength=0.5))

    synth.makeMeasures(inPlace=True)

    # Chord symbols rebuilt from the extracted data.  They go on the Parker
    # staff only -- both staves share the same changes, so repeating them is
    # noise.
    for m_i in range(n_bars):
        abs_bar = start_offset + 4.0 * m_i
        seen: set[tuple[int, str]] = set()
        for beat in (0.0, 1.0, 2.0, 3.0):
            root_pc, q = chord_at(abs_bar + beat)
            if (root_pc, q) in seen:
                continue
            seen.add((root_pc, q))
            m = real.measure(FIRST_MEASURE + m_i)
            if m is not None:
                m.insert(beat, chord_symbol(root_pc, q))

    real.partName, real.partAbbreviation = "Parker", "Parker"
    synth.partName, synth.partAbbreviation = "Synthetic trajectory 1", "Synthetic 1"

    score = stream.Score()
    score.insert(0, metadata.Metadata(title="", composer=""))
    score.insert(0, real)
    score.insert(0, synth)

    out = FIGURES_DIR / "section_notation_real_vs_synth.png"
    render(score, out)

    pct = 100.0 * beat_agreements / len(seq)
    print(f"{n_bars} bars, {len(seq)} sampled events")
    print(f"generated beat token agrees with eighth-grid slot: {pct:.1f}%")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
