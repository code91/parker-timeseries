# CLAUDE.md — agent context for resuming the bebop Markov-chain project

Notes for future Claude sessions on this repo. Read this **before**
touching anything.

---

## What this repo is

A final-exam project for *Dynamical Models for Social Behavior* (MSc
Decision Science, Università di Bari, Profs. Gonnella & Suma). It is
an approved variant of the course's Exercise 2 (random walk on a graph
+ PageRank), applied to a real corpus — 50 Charlie Parker
improvisations from the Aligned Digital Omnibook.

The user is a **first-year MSc** student. The project is scoped much
larger than the suggested exam exercises; the user is aware and uses a
focused subset for the 20-minute presentation. Default to **keeping
the project frozen** — fix bugs, tweak figures, adjust the
presentation. Do **not** add new analyses without being asked.

See `README.md` for the user-facing summary. See `markov_chain/results.md`
for the full prose results. See `markov_chain/presentation.html` for
the print-ready slide deck.

---

## State of the repo (v4)

- Pipeline runs end-to-end in ~60 s via `python markov_chain/run_all.py`.
- 23,143 events extracted (21,590 notes + 1,553 rests), 428 / 520
  states observed, 29 pipeline figures (PNG + PDF) plus 6 standalone
  demo figures.  The deck is 18 numbered slides plus a title, a Backup
  divider and 4 backup slides.
- **v4 removed the within/across split.** There is one operator, `P`.
  See "Further work" in `results.md` for why: the across set's size is
  arithmetic (1 / 6.23 events per chord), it is confounded with the
  downbeat, and 76 % of the chord-change flag is redundant with the state.
- All numerical results match `results.md`. **Smoke test** after any
  change: the V7→I cell `(♭7, dom7, &4) → (3, maj7, ♩1)` ≈ **10.71 %**
  conditional in `P`; τ_mix(P) ≈ 5.4; λ₂ complex with period ≈ 8.4;
  generative r ≈ 0.998; direction effect z ≈ 12.4.

## v3 changes vs v2 (load-bearing)

- The offbeat beat class `&` was split by the integer beat it follows:
  `BEAT_POSITIONS` is now `("1","2","3","4","&1","&2","&3","&4")`. This
  separates the pickup position `&4` (immediately before the next bar and
  usually the next chord) from mid-bar off-beats. `classify_beat` in
  `common.py` is the only place this is decided; there is one call site.
- All 50 tunes are 4/4 with a single time signature and every local offset
  falls in [0, 4), so the "which beat does it follow" question is always
  well defined. Verified, not assumed.
- Consequences: |S| 325 → 520, observed 275 → 428; V7→I cell 13.97 % →
  **15.29 %** and now names one source position, with neighbouring cells at
  ~0; τ_mix(P_within) 46 → 13.8 (partly a smoothing artifact, see below);
  |R| 20 → 73; λ₂(P) became **complex** (period ≈ 8.4 events = one bar of
  eighth notes), which is the metric cycle the old encoding could not express.
- The smoothing mass α·|S| rose from 2.75 to 4.28 against a median row of
  21, so smoothing is roughly twice as influential as in v2. Restricting to
  rows with ≥ 5 observations gives τ_mix(P_within) ≈ 19 rather than 13.8.
  Quote "more than an order of magnitude" for the within/across separation,
  not a precise multiple.

## v2 changes vs v1 (load-bearing)

- State space changed from `(scale_degree, quality, on/off)` to
  `(scale_degree | REST_SD, quality, 1|2|3|4|&)`.
- `REST_SD = "R"` is the sentinel for rest events; rest scale-degree
  is stored as the string "R" both in memory and in the parquet (the
  parquet `scale_degree` column is cast to string at save time).
- Beat positions are `"1"`, `"2"`, `"3"`, `"4"` for integer-beat
  positions (within `BEAT_TOLERANCE`); everything else is offbeat (see
  the v3 note above). `STRONG_BEATS = {"1", "2", "3", "4"}` is the
  equivalent of v1's "on".
- `extract_notes.py` walks both Notes and Rests, then **collapses
  consecutive rest events** into a single event at the start of each
  silence run. This prevents multi-bar silences from dominating the
  operator with rest→rest chains.

---

## Hard invariants — do NOT change without explicit user instruction

1. **`xml/` is source data.** Never modify, regenerate, or delete files
   in `xml/`. The 50 MusicXML files are the ground truth.
2. **No MIDI dependency.** The previous IV pipeline used `midi/`; this
   pipeline does not. Notated MusicXML offsets are intentional — see
   "Beat reference" in the decision log. Don't reintroduce MIDI
   alignment unless asked.
3. **`RNG_SEED = 42` everywhere.** Do not change. Reproducibility is
   load-bearing for the exam.
4. **State ordering is canonical** — sorted lexicographically by
   `(QUALITY_INDEX, scale_degree, beat_index)`. Persisted in
   `data/states.json`. Every operator (`P.npy`, `P_within.npy`,
   `P_across.npy`) is indexed in this order. Re-ordering breaks every
   downstream analysis.
5. **Within/across split conditions on the DESTINATION's
   `chord_changed_from_prev` flag.** A chord change is observed at the
   destination note. Conditioning on the source mis-classifies the
   first note of every new chord. This is the only sensible split.
6. **Smoothing α = 0.01 must stay > 0.** Without smoothing,
   `P̂_across` has zero-rows that break Perron-Frobenius (no unique π)
   and `I − Q` becomes singular (no hitting times).
7. **5 chord-quality classes.** `maj7, min7, dom7, m7♭5, dim7`. Don't
   fold `dim7` into `m7♭5` — the chord-tone sets differ on the 7th
   degree.

---

## Key gotchas (load-bearing)

### music21's `cs.chordKind` is broken on this corpus
The Parker Omnibook encodes chord quality in the
`<kind text="...">` *attribute*, with the element body always set to
`"other"`. music21's `cs.chordKind` reads only the body and returns
the literal string `"other"` for every chord. The original
`musicxml_to_pcs.PCSExtractor` (now removed) silently dropped chord
quality because of this.

**Fix used in `markov_chain/extract_notes.py`**: read
`cs.chordKindStr` (which exposes the `text` attribute), with a regex
fallback over `cs.figure`. Mapping in
`markov_chain/common.py::KIND_TEXT_MAP`. Census of all 8 distinct
`text` values across the corpus:

| text | count | class |
|---|---|---|
| `7` | 2,873 | dom7 |
| `m` | 1,437 | min7 |
| *(empty)* | 873 | maj7 |
| `dim` | 43 | dim7 |
| `-7b5` | 39 | m7♭5 |
| `m7b5` | 6 | m7♭5 |
| `6` | 1 | maj7 |
| `/G` | 1 | unmappable → excluded with warning |

If a tune is added or replaced and brings a new `text` value, extend
`KIND_TEXT_MAP` in `common.py` — don't try to add fallback regex logic
in `extract_notes.py`.

### Tied notes collapse to onset
Skip notes where `n.tie is not None and n.tie.type in ("stop",
"continue")`. Only `tie.type == "start"` (or `tie is None`) is
counted, exactly once at the onset.

### Tune boundaries
`build_count_matrices` iterates `for tune_id, grp in
df.groupby("tune_id", sort=False)` and counts `t → t+1` only within
each group. 50 tunes → 50 boundaries skipped → 21,540 transitions
(check matches `data/section1_summary.json`).

### Parquet can't store tuple columns
`extract_notes.py` serializes the `state` column as the pipe-delimited
string `"d|q|b"`. `common.load_notes()` re-hydrates it back to tuples.
Don't read `data/notes.parquet` directly with `pd.read_parquet` — use
`common.load_notes()`.

### scipy.linalg.eig overload-typing
Pyright complains about the tuple-return overload of `scipy.linalg.eig`
in three files (`02_stationary.py`, `03_spectral.py`, `05_voice_leading.py`,
`06_null_comparison.py`). The runtime is fine — these are stub
limitations, not real bugs. Don't add casts/type-ignore unless asked.

---

## Repo layout (recap)

```
parker-chains/
├── markov_chain/                # All project code
├── data/                        # Generated artifacts
├── figures/                     # 27 figures, PNG + PDF, 300 dpi
├── xml/                         # Source MusicXML — never modify
├── exam_exercises_list.pdf      # Exam definition
├── README.md
└── CLAUDE.md                    # (this file)
```

Anything not in this list was intentionally deleted. Specifically
removed: the previous IV-pipeline scripts (`00_match_titles.py` …
`11_robustness.py`), all `parker_*.csv` / `parker_*.json` outputs,
`pipeline*.html`, `midi/`, `mp3/`, `other/` (source-data zips +
references), `readme.md` (old project's README), `tune_titles.csv`
(unused). Do **not** restore any of these.

---

## Module map

| File | Purpose | Reads | Writes |
|---|---|---|---|
| `common.py` | Shared utilities, all tunable parameters, IO | — | — |
| `extract_notes.py` | MusicXML → per-event dataset (stores `pitch_midi` for Section 12) | `xml/*.xml` | `data/notes.parquet` |
| `01_transition_matrices.py` | Build P̂, P̂_within, P̂_across | `data/notes.parquet` | `data/P*.npy`, `data/N*.npy`, `data/states.json`, `figures/section1_*`, `data/section1_summary.json` |
| `02_stationary.py` | π via left eigenvector at λ=1 | `data/P*.npy`, `data/states.json` | `data/pi_*.npy`, `figures/section2_*`, `data/section2_summary.json` |
| `03_spectral.py` | Eigenvalues, mixing time, v₂ | `data/P*.npy`, `data/states.json` | `data/eigvals_*.npy`, `figures/section3_*`, `data/section3_summary.json` |
| `04_hitting_times.py` | h = (I−Q)⁻¹·1 to R | `data/P*.npy`, `data/states.json` | `data/hitting_*.npy`, `figures/section4_*`, `data/section4_summary.json` |
| `05_voice_leading.py` | Top-20 across + V7→I cell | `data/P*.npy`, `data/states.json` | `figures/section5_*`, `data/section5_summary.json` |
| `06_null_comparison.py` | χ² + KL vs **two** permutation nulls: shuffle-everything, and a beat-preserving null that holds each tune's beat sequence fixed and permutes (degree, quality) within beat class | `data/notes.parquet`, `data/N*.npy`, `data/states.json` | `figures/section6_*`, `data/section6_summary.json` |
| `07_memory_order.py` | Order-1 vs order-2 (BIC + held-out) | `data/notes.parquet`, `data/states.json` | `figures/section7_*`, `data/section7_summary.json` |
| `08_hub_structure.py` | PageRank, degree, betweenness | `data/P*.npy`, `data/N*.npy`, `data/states.json` | `figures/section8_*`, `data/section8_summary.json` |
| `09_generative_validation.py` | 1000 simulated trajectories | `data/notes.parquet`, `data/P.npy`, `data/pi_P.npy`, `data/states.json` | `figures/section9_*`, `data/section9_summary.json` |
| `build_presentation_data.py` | Aggregate headline numbers | `data/section*_summary.json`, `data/states.json`, `data/notes.parquet` | `markov_chain/presentation_data.json` |
| `10_distribution_evolution.py` | μ₀ = e_i, iterate μP, converge to π | `data/P.npy`, `data/pi_P.npy` | `figures/section10_*`, `data/section10_summary.json` |
| `11_graph_view.py` | Induced subgraph on the 8 busiest states | `data/P.npy`, `data/N.npy`, `data/pi_P.npy` | `figures/section11_*`, `data/section11_summary.json` |
| `12_direction.py` | Descending vs ascending chord-tone landing | `data/notes.parquet` | `figures/section12_*`, `data/section12_summary.json` |
| `13_absorption_recurrence.py` | Absorption probabilities B = (I−Q)⁻¹R (which resolved state is reached first) and Kac recurrence times 1/π | `data/P.npy`, `data/hitting_P.npy`, `data/pi_P.npy`, `data/states.json` | `data/absorption_P.npy`, `data/recurrence_P.npy`, `figures/section13_*`, `data/section13_summary.json` |
| `run_all.py` | Orchestrator | — | (re-runs every step) |

Standalone scripts, **not** in `run_all.py` — run them by hand after a
pipeline rerun, since they read its artifacts:

| File | Purpose | Reads | Writes |
|---|---|---|---|
| `intro_encoding_demo.py` | Notes → states walkthrough for the state-space slide | `xml/3zn4c.xml` | `figures/section_intro_encoding.*` |
| `corpus_stats_demo.py` | Beat distribution + solo-length histogram | `data/notes.parquet` | `figures/section_corpus_stats.*` |
| `notation_demo.py` | Parker vs a sampled trajectory, engraved via music21 → MuseScore | `data/notes.parquet`, `data/section9_plot_trajectory.npy`, `xml/3zn4c.xml` | `figures/section_notation_real_vs_synth.*` |
| `matrix_excerpt_demo.py` | The operator as a grid: full heatmap plus a 12x12 block with printed values | `data/P.npy`, `data/states.json` | `figures/section_matrix_excerpt.*` |
| `state_trajectory_demo.py` | Trajectory plotted as state index, not the scale-degree projection | `data/notes.parquet`, `data/section9_plot_trajectory.npy` | `figures/section_state_trajectory.*` |
| `missing_states.py` | The unobserved cells: scarcity vs structural zeros | `data/notes.parquet`, `data/states.json` | `data/missing_states_summary.json`, `figures/section_missing_states.*` |

`notation_demo.py` engraves the *same* trajectory that section 9 plots, so
`09_generative_validation.py` must run first (it writes
`data/section9_plot_trajectory.npy`). MuseScore 4's CLI ignores `-S` style
files and drops MusicXML system breaks on import, so the excerpt length is
tuned to what fits one system rather than forced by layout.

---

## Common operations

### Add a new figure to an existing section
- Section files create figures inline. Add a new `plot_xxx()` function
  in the same file and call it from `main()`. Save as both PNG and PDF
  via `fig.savefig(out.with_suffix(".png"))` then
  `.with_suffix(".pdf")`. Use `dpi=300` (already set globally via
  `plt.rcParams`).
- File name convention: `figures/section{N}_{operator}_{descriptor}.png`.

### Tune a parameter
All tunables at the top of `markov_chain/common.py`:
`SMOOTHING_ALPHA`, `BEAT_TOLERANCE`, `UNDERSAMPLED_ROW_THRESHOLD`,
`RNG_SEED`. Changing any of these requires a full `run_all.py` rerun.
**Document the change** in `results.md` decision log.

### Change a chord-quality mapping
Edit `KIND_TEXT_MAP` in `common.py`. If adding a new class, also
extend `QUALITY_CLASSES` and `CHORD_TONES`. Then full rerun.

### Re-render figures with new color scheme
Change the `plt.rcParams.update(...)` blocks at the top of each
`0N_*.py` file, then `python markov_chain/run_all.py`. The slide deck
uses crimson `#9b111e` as its single accent (on white background); the
figures currently use matplotlib's `#3b6fb6` blue and `#c0392b` red.
They harmonize visually but if the user asks for exact crimson match,
sweep all `color="..."` arguments.

### Edit the presentation
`markov_chain/speaker_notes.html` is the slide-by-slide script; render it
with headless Chrome `--print-to-pdf` to refresh `speaker_notes.pdf`.
It carries per-slide timings that must be renumbered whenever a slide is
inserted or removed.

`markov_chain/presentation.html` is a single self-contained HTML file
with embedded CSS. 16:9 fixed-size slides, one per printed page via
`@page` + `page-break-after: always`. CSS variables at the top of
`<style>` — change palette there, not per-slide.
Figure references are relative: `../figures/...`. Don't break that.

### Verify nothing regressed after a change
1. `python markov_chain/run_all.py` should complete with exit 0 in
   ~50 s.
2. Check `markov_chain/presentation_data.json`:
   - `corpus.total_notes` == **23143** (the field is named "total_notes"
     for backwards compatibility but actually counts notes + rests)
   - `corpus.states_observed` == **428**
   - `v7_to_I_cells["(b7, dom7, &4) -> (3, maj7, ♩1)"].conditional`
     ≈ **0.1071**
   - `spectral.P.mixing_time_steps` ≈ **5.4**
   - `generative_validation.pearson_r_f_sim_vs_pi` ≈ **0.998**
3. `ls figures/*.png | wc -l` should equal **26** (29 from `run_all.py`,
   plus `parker.png`, `scrapple.png` and the demo-script figures).

If any of those drift by more than rounding noise, find what changed
before declaring success.

---

## What NOT to do

- Don't add a web framework, GUI, or interactive notebook unless asked.
  The current pipeline is plain Python scripts + matplotlib.
- Don't restore the IV pipeline (`00_*` … `11_*`). It was intentionally
  removed.
- Don't introduce MIDI as a beat reference. The decision is "notated,
  not performed" — see `results.md` decision log.
- Don't add per-tune analyses (cluster of strategies, autocorrelation,
  etc.) — those belong to the old project.
- Don't change the within/across split definition.
- Don't add unrequested abstractions or "improvements". The user is
  presenting this for a 20-min talk; the simpler it is, the easier to
  defend.
- Don't write new markdown documentation unless the user asks for it.
  Anything not in `README.md` / `CLAUDE.md` / `results.md` /
  `presentation.html` is probably noise.

---

## Pacing for future Claude

The user moves fast and says "go". Match that energy. Default rules:

- Read state before acting. Confirm via `presentation_data.json` and
  `results.md` before assuming results have changed.
- Be explicit about destructive operations and ask first.
- Match the existing style: serif fonts in figures (`font.family =
  'serif'`), crimson accent in the slide deck, no emojis anywhere.
- Don't add comments to code unless they document a non-obvious
  *why* (load-bearing invariant, music21 gotcha, etc.).
