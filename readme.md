# Bebop as a Markov Chain

> Final-exam project for *Dynamical Models for Social Behavior*
> (Università di Bari, MSc Decision Science, Profs. Gonnella & Suma).
> Approved variant of exam **Exercise 2** — *Random walk on a graph &
> PageRank* — applied to a real corpus.

A discrete-time finite-state Markov chain over **(scale-degree-or-rest,
chord quality, beat position)** triples extracted from the Charlie Parker
Aligned Digital Omnibook. 50 tunes, 23,143 events (21,590 notes + 1,553
rests), 275 observed states. Beat position is 5-class
({♩1, ♩2, ♩3, ♩4, &}) — preserves strong/weak downbeat distinction.

**Status:** complete and reproducible.  `python markov_chain/run_all.py`
regenerates everything from `xml/` in ~50 seconds.

---

## Headline findings

| | Result |
|---|---|
| **V7 → I voice leading** | Conditional Pr((3, maj7, ♩1) \| (♭7, dom7, &), chord-change) = **13.97 %** — bebop's textbook half-step resolution as a single matrix cell, with the target sharpened to specifically beat 1 |
| **Two mixing regimes** | τ<sub>mix</sub>(P̂<sub>within</sub>) ≈ **46 steps** vs τ<sub>mix</sub>(P̂<sub>across</sub>) ≈ **1.4 steps** — 32× spread |
| **Gravity quantified** | Expected hitting time from the ♭9-over-dom7 state to the chord-tone resolution set: **1.59 events** |
| **Phrase-end pattern** | Top across-chord transition: (5, dom7, ♩3) → (rest, min7, ♩1) at **64.65 % conditional** — Parker lands on 5-of-V on beat 3, then rests at the start of the next chord. The chain rediscovers the canonical bebop phrase-end. |
| **Hub structure** | Under P̂<sub>across</sub>: **10/10 top in-degree hubs on a strong beat (1-4)**, 9/10 top out-degree hubs on the off-grid `&` — near-binary saturation of the "& launches, strong beat lands" rule |
| **Order-2 effect** | In-sample ΔBIC favors order-2 strongly for every operator (P̂ +21,844, P̂<sub>within</sub> +13,651, P̂<sub>across</sub> +8,336) — real but un-exploitable for prediction at 23k events |
| **Generative validation** | Pearson r(f<sub>sim</sub>, π) = **0.9992**, TV = 0.022 over 100k sampled steps |

Full numerical results in [`markov_chain/results.md`](markov_chain/results.md).
Slides in [`markov_chain/presentation.html`](markov_chain/presentation.html).
Headline numbers as JSON in `markov_chain/presentation_data.json`.

---

## Quick start

Dependencies: Python ≥ 3.10 with `numpy`, `scipy`, `pandas`,
`matplotlib`, `networkx`, `music21`, `pyarrow`. Source data in `xml/`
(50 MusicXML files from the Parker Omnibook).

```bash
python markov_chain/run_all.py
```

This runs in order:

```
extract_notes.py                MusicXML → data/notes.parquet      (~2 s)
01_transition_matrices.py       P, P_within, P_across + heatmaps
02_stationary.py                π via Perron-Frobenius
03_spectral.py                  λ_2, mixing time, second eigenvector
04_hitting_times.py             h = (I-Q)⁻¹·1 to resolution set R
05_voice_leading.py             Top-20 across transitions + V7→I cell
06_null_comparison.py           1,000-perm null, χ² and KL          (~26 s)
07_memory_order.py              Order-1 vs order-2 (BIC + held-out)
08_hub_structure.py             PageRank, degree, betweenness
09_generative_validation.py     1,000 simulated trajectories
build_presentation_data.py      Aggregates headline numbers
```

All scripts are deterministic (`RNG_SEED = 42`). Clean re-run from
scratch: `rm -rf data/*.npy data/*.json data/*.parquet figures/* && python markov_chain/run_all.py`.

---

## Repo layout

```
parker-chains/
├── markov_chain/                # All project code
│   ├── common.py                state space, chord-tone map, IO helpers,
│   │                            all tunable parameters at the top
│   ├── extract_notes.py         MusicXML → per-note dataset
│   ├── 01_transition_matrices.py
│   ├── 02_stationary.py
│   ├── 03_spectral.py
│   ├── 04_hitting_times.py
│   ├── 05_voice_leading.py
│   ├── 06_null_comparison.py
│   ├── 07_memory_order.py
│   ├── 08_hub_structure.py
│   ├── 09_generative_validation.py
│   ├── build_presentation_data.py
│   ├── run_all.py               Orchestrator
│   ├── presentation.html        Print-ready 16:9 slide deck
│   ├── presentation_data.json   Headline numbers
│   └── results.md               Full prose results
├── data/                        Generated artifacts (gitignored target)
│   ├── notes.parquet            21,590 notes
│   ├── P.npy / P_within.npy / P_across.npy
│   ├── N.npy / N_within.npy / N_across.npy
│   ├── pi_*.npy / eigvals_*.npy / hitting_*.npy
│   ├── states.json              Canonical state ordering
│   └── section{1..9}_summary.json
├── figures/                     Generated artifacts (gitignored target)
│   └── *.png + *.pdf            27 figures, 300 dpi
├── xml/                         Source MusicXML (50 tunes) — required
├── exam_exercises_list.pdf      Exam definition
├── README.md                    (this file)
└── CLAUDE.md                    Notes for future Claude sessions
```

---

## Defensible decisions (decision log)

Each is presented as one slide in the deck and discussed in `results.md`.

| Choice | Decision | One-line rationale |
|---|---|---|
| Chord-quality classes | **5**: maj7, min7, dom7, m7♭5, dim7 | Folding "dim" into m7♭5 misrepresents the 7th degree (♭♭7 vs ♭7) for 43 chord events |
| `"m"` → min7, `""` → maj7 | bebop lead-sheet convention | Bare `m` in a 4-note bebop context implies min7; surrounding chord tones confirm 7ths are routinely played |
| Beat-position tolerance | **0.05** quarter-notes | Absorbs grace notes and rounding without leaking "and"-of-beat eighths into the strong-beat class |
| Beat-position granularity | **5 classes** (1, 2, 3, 4, &) | Preserves the strong/weak downbeat distinction that bebop voice-leading exploits |
| Rest handling | **Rests as states; consecutive rests collapsed** | Captures phrasing structure; collapsing prevents multi-bar silences from dominating the operator |
| Beat reference | MusicXML **notated** offset (not MIDI) | Notated beat is what bebop theorists mean by "on the beat" |
| Laplace smoothing α | **0.01** | Observed transitions dominate every row; large enough for Perron-Frobenius irreducibility and `I − Q` invertibility |
| Within/across split | conditioned on the **destination**'s chord-change flag | A chord change is observed at the destination note |
| BIC parameter count | **observed cells** | Penalizes only the parameters the model actually uses; theoretical n²(n−1) ≈ 5.5M wildly overpenalizes order-2 |

---

## Limitations

- 21,590 notes is enough for first-order analysis but marginal for
  second-order (held-out test favors order-1 despite large in-sample
  ΔBIC).
- Beat position is binary; finer phase labels (1, 2-and, 3, …) would
  quadruple the state space.
- Quality mapping discards 7th-degree alterations on dominants (alt,
  ♯11, ♭9 all collapse to `dom7`).
- MIDI tempo and swing are ignored — notated beat only.
- No transitions across tune boundaries — correct for the model
  definition but means tune-level structure (head vs chorus) is out of
  scope.

---

## Corpus license

The Charlie Parker Aligned Digital Omnibook is released under
CC BY-NC-SA 2.0 (Déguernel, Vincent, Assayag — Inria / STMS Lab
Ircam/CNRS/UPMC). Original transcriptions © Atlantic Music Corp.
Source data not redistributed in this repository.
