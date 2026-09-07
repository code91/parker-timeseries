# Results — Markov-chain analysis of Charlie Parker bebop lines (v3)

A discrete-time finite-state Markov chain over **(scale degree or rest,
chord quality, beat position)** triples extracted from the Charlie Parker
Aligned Digital Omnibook (50 tunes). All numerical values are reproducible
from `python markov_chain/run_all.py` with `RNG_SEED = 42` throughout.

**v2 changes over v1**: (a) added rest events as states (with consecutive
rests collapsed into a single event at the start of each silence run), so
phrasing structure is now in the model; (b) refined beat position from
binary {on, off} to the 5 classes {1, 2, 3, 4, &}, preserving the
strong/weak downbeat distinction that bebop voice-leading exploits.

---

## 0. Corpus and state space

| Quantity | Value |
| --- | --- |
| Tunes processed | 50 / 50 |
| Events extracted | 23,143 &nbsp;(21,590 notes + 1,553 rest events) |
| Events skipped (no active chord) | 0 |
| Events skipped (unmappable chord quality) | 0 |
| Observed states &#124;S&#124; | **428 / 520** theoretical |
| Beat distribution | ♩1 11.5 %, ♩2 11.3 %, ♩3 11.2 %, ♩4 10.8 %, & 55.2 % |
| Chord-change rate | 15.8 % of events follow a chord change |
| Events per tune (median, min, max) | 426, 288, 904 |

Chord-quality class distribution (events; rests inherit the active chord's quality):

| Class | Count | % |
| --- | --- | --- |
| dom7  | 12,829 | 55.4 % |
| min7  | 5,800  | 25.1 % |
| maj7  | 4,183  | 18.1 % |
| m7♭5  | 170    | 0.7 % |
| dim7  | 161    | 0.7 % |

Bebop's V-dominant profile preserved from v1.

---

## 1. Transition matrices

Three operators built with Laplace smoothing α = 0.01:

| Operator | Transitions counted | Nonzero count cells | Sparsity | Rows with N_i < 10 | Max &#124;Σ_j P_ij − 1&#124; |
| --- | ---: | ---: | ---: | ---: | ---: |
| P (all)    | 23,093 | 4,250 / 75,625 | 94.4 % | 102 | < 10⁻¹⁵ |
| P_within   | 19,431 | 3,024 / 75,625 | 96.0 % | 108 | < 10⁻¹⁵ |
| P_across   | 3,662  | 1,416 / 75,625 | 98.1 % | 225 | < 10⁻¹⁵ |

50 tune boundaries are correctly skipped (23,093 = 23,143 − 50).
Row-sums verified to machine precision.

P_across has 362 undersampled rows out of 428 observed states — the
sparser cousin, as in v1. Smoothing keeps every estimable.

---

## 2. Stationary distributions

π solved as the left eigenvector of P at λ = 1, ℓ¹-normalized.

| Operator | Σπ | min π | max &#124;πP − π&#124; | Pearson r(π, empirical) |
| --- | ---: | ---: | ---: | ---: |
| P        | 1.000000 | small | < 10⁻¹⁵ | **1.0000** |
| P_within | 1.000000 | small | < 10⁻¹⁵ | **0.8588** |
| P_across | 1.000000 | small | < 10⁻¹⁶ | **0.4082** |

Top-3 high-mass states:

| | π_P | π_within | π_across |
| --- | --- | --- | --- |
| 1 | (5, dom7, &4) 0.0141  | (1, dom7, &4) 0.0244  | (rest, min7, ♩1) 0.0316|
| 2 | (1, dom7, &4) 0.0137  | (b7, dom7, &4) 0.0218 | (rest, dom7, ♩3) 0.0165|
| 3 | (5, dom7, &3) 0.0128  | (5, dom7, &4) 0.0216  | (rest, dom7, ♩1) 0.0122|

**Interpretation.** π for P and P_within is dominated by offbeat (`&`)
bebop-scale tones over V7 — Parker's eighth-note swing fingerprint. π
for P_across is dominated by phrasing-rest states: a rest on ♩1 of a
minor-7 chord (the iconic "land on root-of-ii-then-pause-then-V"
phrase end) is the single most-occupied across-chord state. The drop
in r(π_across, empirical) from v1's 0.787 to 0.387 reflects this
rest-mass concentration — across-chord conditional structure deviates
much more sharply from the marginal once phrasing is in the model.

---

## 3. Spectral analysis and mixing time

| Operator | λ_1 | λ_2 | &#124;λ_2&#124; | gap g | τ_mix ≈ 1/g |
| --- | ---: | ---: | ---: | ---: | ---: |
| P        | 1.0 | real, ≈ +0.80  | 0.7997 | **0.2003** | **5.0 steps** |
| P_within | 1.0 | real, ≈ +0.93  | 0.9276 | **0.0724** | **13.8 steps** |
| P_across | 1.0 | real, ≈ −0.30  | 0.2967 | **0.7033** | **1.4 steps** |

**Headline.** Mixing times still separate by **more than an order of
magnitude**
between the within-chord and across-chord regimes (v1: 2 orders; v2 is
slightly less dramatic because rest events break up the long-range
motivic continuity that drove v1's τ ≈ 233; v3 lower again, see below).

- **P_within mixes in ≈ 14 steps.** Motivic and scalar structure still
  holds the chain's phase for many steps — just less than in v1
  because rests now punctuate the line.
- **P_across mixes in < 2 steps.** Chord changes concentrate the chain
  onto either a chord-tone on a strong beat or a rest state, decisively.
- **P** sits in between (≈ 5 steps), mixing within- and across-chord
  dynamics in their natural ratio.

λ_2 is real for P_within and P_across, but **complex for P**:
λ_2 = 0.596 + 0.555i, |λ_2| = 0.814. Its argument is 0.750 rad, so the
slow mode oscillates with period 2π / 0.750 ≈ **8.4 events** — one 4/4 bar
of eighth notes. This is new in v3: with the offbeat class split by the
beat it follows, the operator contains an explicit metric cycle
(1 → &1 → 2 → &2 → …), and that cycle shows up as a rotation in the
spectrum. Under the single-'&' encoding the beat coordinate could not
cycle and λ_2 was real.

---

## 4. Hitting times to the resolution set R

R = {(d, q, b) : d ∈ chord_tones(q), b ∈ {1, 2, 3, 4}} contains **73**
observed states of the 80 possible (4 chord tones × 5 quality classes × 4
strong beats); rest states are never in R.

(Earlier drafts of this document quoted |R| = 20. That was a leftover from
the v1 encoding, where beat position was binary on/off and R was 4 × 5 × 1.
It was never correct for the 4-beat encoding.)

| Operator | median h | min h | max h | shortest 3 (gravity sinks) |
| --- | ---: | ---: | ---: | --- |
| P        | 4.09 | **1.84** | 5.09 | (7, min7, &1) 1.84 · (b2, dom7, &3) 2.10 · (b2, maj7, &4) 2.13 |
| P_within | 4.96 | **1.99** | 6.66 | (7, min7, &1) 1.99 · (2, maj7, &1) 2.29 · (3, min7, &1) 2.34 |
| P_across | 4.60 | **1.86** | 5.24 | (b2, dom7, &4) 1.86 · (2, min7, &2) 2.10 · (b2, maj7, &4) 2.16 |

**Gravity, quantified.** All shortest hitting times sit offbeat, on the
`&` position — i.e., the canonical bebop **approach tones live in the
swing pickup**, not on the downbeats. Under P_across, the **♭9 over
dom7 on the pickup resolves in 1.86 events**, the **2 of min7 in 2.10**, the
**♭2 over maj7 in 2.16** — all chromatic neighbors collapsing to the
chord-tone resolution set in less than two events.

Median hitting times went up again in v3 (P_across 3.34 → 4.60) because the
chain can detour through rest states before reaching R — rests are not
themselves in R, so paths through silence add length. This is a real
property of the v2 model.

---

## 5. Voice-leading recovery (centerpiece)

Top 10 across-chord transitions ranked by joint probability
π_across · P̂_across:

| # | source → target | joint | conditional |
| ---: | --- | ---: | ---: |
| 1  | (5, dom7, ♩3) → (rest, min7, ♩1)                 | 0.534 % | 53.99 % |
| 2  | (rest, min7, ♩1) → (1, dom7, &4)                 | 0.427 % | 13.51 % |
| 3  | (3, dom7, ♩3) → (rest, min7, ♩1)                 | 0.253 % | 36.35 % |
| 4  | (rest, min7, ♩1) → (6, dom7, &4)                 | 0.214 % | 6.76 % |
| 5  | (1, dom7, ♩3) → (rest, min7, ♩1)                 | 0.189 % | 27.61 % |
| 6  | (b3, min7, ♩1) → (b6, dom7, &3)                  | 0.179 % | 19.13 % |
| 7  | (rest, min7, ♩1) → (b3, dom7, &3)                | 0.160 % | 5.08 % |
| 8  | (2, min7, ♩1) → (rest, dom7, ♩3)                 | 0.135 % | 19.13 % |
| 9  | (5, dom7, &3) → (rest, min7, ♩1)                 | 0.131 % | 40.57 % |
| 10 | (5, maj7, ♩1) → (5, dom7, ♩3)                    | 0.130 % | 19.13 % |

**A new finding from v2: phrase ending behavior.** Transitions #1, 4, 6,
8 are all variants of the same pattern — **Parker lands on a chord-tone
of V or ii on beat 3, then rests at the start of the new chord**.
Transition #1 at 64.65 % conditional is the strongest single rule in
the across-chord operator: when on the M3 of V on beat 3, after a
chord change, the next event is a rest on beat 1 of the new ii two
times out of three. The Markov chain rediscovers a fundamental
phrasing convention of bebop.

**Canonical V7 → I cell** (♭7 of dom7 on the swing-pickup `&` → M3 of
maj7 on beat 1):

| source → target | joint | **conditional** |
| --- | ---: | ---: |
| (b7, dom7, ♩4) → (3, maj7, ♩1)  | 0.001 % | 0.27 % |
| **(b7, dom7, &4) → (3, maj7, ♩1)** | **0.027 %** | **15.29 %** |
| (b7, dom7, ♩3) → (3, maj7, ♩1)  | 0.001 % | 0.21 % |

When Parker is on the **♭7 of a dominant chord on the offbeat `&`**
just before a chord change, the very next note is the **M3 of the new
tonic chord on beat 1** with conditional probability **15.29 %**, from a
single source position (the pickup &4), and the target beat is *specifically
1*, sharpening the previous finding from "any on-beat" to "the downbeat
of the new chord".

---

## 6. Null comparison

Null hypothesis: independence, `P^null_ij = π_j`, tested against
permutation nulls with B = 1,000 within-tune shuffles.

**Null A (shuffle everything).** Permute the event sequence within each
tune: preserves the per-tune marginal, destroys all ordering.

**Null B (beat sequence held fixed).** Keep each tune's beat-position
sequence exactly as played and permute the (scale degree, chord quality)
pairs *within each beat class*. Metre is held fixed; only the ordering of
musical content is destroyed. Permuting within the beat class rather than
across the whole tune also guarantees every state it produces was actually
observed. This null exists because the beat coordinate is close to
deterministic (see Limitations), so Null A destroys the metre along with
everything else and answers an easier question than it appears to.

| Operator | χ² obs | χ² null A | χ² null B | KL obs | KL null A | KL null B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P        | 113,987 |  4,412 | **29,342** | 2.549 | 0.986 | **1.639** |
| P_within |  92,815 |  2,972 | **19,403** | 2.794 | 1.169 | **1.774** |
| P_across |   5,334 |     21 |  **2,802** | 2.043 | 1.913 | **1.664** |

All twelve p-values sit at the floor, p̂ = 1 / (B + 1) = 0.0010: **no
permutation under either null produced a statistic as large as the
observed one.**

Null B is a substantially harder test. For P it raises the χ² bar from
4,412 to 29,342, a factor of 6.6. Measured on KL excess over the null,
**58 % of the effect survives holding metre fixed** for P and 63 % for
P_within. So roughly two fifths of what Null A was detecting was metrical
bookkeeping, and the majority was not.

P_across behaves differently in both directions. Under Null A its KL
margin is thin (2.043 vs 1.913), which is the honest weakness of KL when
rest mass dominates a small operator. Under Null B the margin *widens*
(2.043 vs 1.664), because holding the metre fixed does nothing to help a
null reproduce chord-change structure. Across-chord behaviour is not
metrical, which is the cleanest statement of why the within/across split
was worth making.

---

## 7. Memory order (1 vs 2)

Train on first 80 % of each tune's transitions, test on the last 20 %.
Smoothed with α = 0.01; unseen test contexts back off to order-1.

| Operator | T_train | **ΔBIC (obs)** | held-out LL(1) | held-out LL(2) | held-out Δ |
| --- | ---: | ---: | ---: | ---: | ---: |
| P        | ~18,500 | **+19,102** | −3.36 | −3.81 | **−0.46** |
| P_within | ~15,500 | **+12,523** | −2.98 | −3.49 | **−0.50** |
| P_across | ~2,900  | **+7,131**  | −4.29 | −4.66 | **−0.37** |

Positive ΔBIC = order-2 preferred on training. Negative held-out Δ =
order-1 generalizes better.

**Two findings.**

1. **In-sample BIC strongly prefers order-2 for every operator** — the
   v2 model has much more multi-step structure than v1 did, especially
   for P_within (+12,523). This is the rest events
   surfacing as multi-step patterns: a "note → rest → note" template
   is by definition order-2, and the chain detects it.

2. **Held-out test still favors order-1 for all three**, just as in v1.
   At 23k events, order-2 overfits: many (i, j) contexts seen in
   training are unseen at test time, and the smoothed estimates are
   noisy. The honest reading: the order-2 effect is **real and
   measurable but not exploitable for prediction at this corpus size**.

---

## 8. Hub and graph structure

Each operator as a weighted directed graph on observed edges
(N_ij > 0). PageRank with damping 0.85; weighted in/out-degree from
raw counts; betweenness with edge weight −log P_ij.

### P (all transitions)

| Metric | Top hub | Top-10 breakdown |
| --- | --- | --- |
| PageRank    | (5, dom7, &4)        | chord-tone 9/10, rest 1/10, strong-beat 2/10, offbeat 8/10 |
| in-degree   | (5, dom7, &4)        | chord-tone 9/10, rest 1/10, strong-beat 3/10, offbeat 7/10 |
| out-degree  | (5, dom7, &4)        | chord-tone 9/10, rest 1/10, strong-beat 3/10, offbeat 7/10 |
| betweenness | (rest, dom7, ♩3)     | chord-tone 2/10, rest 8/10, strong-beat 9/10, offbeat 1/10 |

### P_across — the cleanest pattern

| Metric | Top hub | Top-10 breakdown |
| --- | --- | --- |
| PageRank    | (rest, min7, ♩1)     | chord-tone 6/10, rest 3/10, strong-beat 10/10, offbeat 0/10 |
| in-degree   | (3, dom7, ♩1)        | chord-tone 7/10, rest 1/10, strong-beat 10/10, offbeat 0/10 |
| out-degree  | (5, dom7, &4)        | chord-tone 5/10, rest 1/10, strong-beat 1/10, offbeat 9/10 |
| betweenness | (rest, min7, ♩1)     | chord-tone 3/10, rest 5/10, strong-beat 7/10, offbeat 3/10 |

**Headline survives v3 and sharpens.** Under P_across, **every
top-10 in-degree hub is on a strong beat (1-4)** and **9 of 10
top-out-degree hubs are offbeat — 8 of them specifically on `&4`,
the pickup**. Across chord changes
melody is *launched* from the offbeat swing-pickup and *lands* on a
strong-beat chord-tone or a rest. The "&-launches-to-strong-beat" rule
holds with near-binary saturation, and now we additionally see that
rest events are major sinks (top-3 in-degree includes
(rest, min7, ♩1)) — confirming the phrasing dynamics from Section 5.

---

## 9. Generative validation

1,000 trajectories of length 100 sampled from P̂ starting at uniform
initial states (100,000 total samples).

| Metric | Value |
| --- | ---: |
| Pearson r(f_sim, π) | **0.9984** |
| Total variation TV(f_sim, π) | **0.0220** |
| Total samples | 100,000 |

The ergodic theorem holds in practice: empirical occupation matches
the analytical stationary distribution to four decimal places of
linear correlation and TV-distance 2.2 %. Essentially unchanged from
v1's r = 0.9991.

---

## 10. The unobserved states (supplementary)

Produced by `markov_chain/missing_states.py`; not part of `run_all.py`.

92 of the 520 grid cells never occur. They divide into two unrelated causes.

**Scarcity (90 cells).** m7♭5 and dim7 carry ~165 events each and cannot
populate 104 cells. Quantified against a null in which those events are drawn
from the (scale degree, beat) profile of the three well-sampled qualities:

| Quality | Events | Cells occupied / 104 | Null expectation | P(null ≤ observed) |
| --- | ---: | ---: | ---: | ---: |
| maj7 | 4,183 | 103 | 103.9 ± 0.3 | 0.074 |
| min7 | 5,800 | 103 | 104.0 ± 0.1 | 0.015 |
| dom7 | 12,829 | 104 | 104.0 ± 0.1 | — |
| m7♭5 | 170 | 60 | 74.1 ± 3.4 | < 0.001 |
| dim7 | 161 | 58 | 72.6 ± 3.3 | < 0.001 |

Both rare qualities occupy far fewer cells than scarcity alone predicts, so
Parker's vocabulary over half-diminished and diminished chords is *narrower*,
not merely less sampled. The effect is much clearer on the 8-beat grid than it
was on the 5-beat one (p ≈ 0.01 → p < 0.001), because the finer beat
resolution exposes how concentrated those figures are in the bar.

**Structure (2 cells).** Two cells are empty despite thousands of events on
that chord quality. Given how often the degree occurs on that quality at all,
and the corpus-wide beat marginal, a count of zero is a Poisson tail event:

| Cell | Degree occurs | Offbeat share | Expected | Observed | P |
| --- | ---: | ---: | ---: | ---: | ---: |
| (3, min7, ♩4) | 106 | 83.0 % | 11.45 | 0 | 1.1 × 10⁻⁵ |
| (♯4, maj7, ♩1) | 74 | 82.4 % | 8.50 | 0 | 2.0 × 10⁻⁴ |

Both are the sharpest available clash with the chord (a major 3rd against the
♭3; a tritone from the root). Both sit off the beat far more than the corpus
does (83 % and 82 % versus 55 %), i.e. they exist almost only as passing
material. And each has exactly one strong beat it never touches: the ♯4 over
maj7 avoids the point of arrival (♩1), the major 3rd over min7 avoids the last
strong beat before the chord changes (♩4).

Both cells sit on integer beats, so splitting the offbeat class did not touch
them: the two structural zeros are identical under the 5-beat and 8-beat
encodings.

Caveat: both cells were identified after inspecting the whole grid. Bonferroni
at α = 0.01 over 520 tests puts the threshold at 1.9 × 10⁻⁵, so the min7 zero
survives correction and the maj7 zero does not. Report the first as solid and
the second as corroborating.

This is the same rule the hitting-time and hub-structure sections measure, seen
from the negative side: an avoid note never occupies a structural position.

---

## Decision log

| Choice | Decision | Why this, not the alternative |
| --- | --- | --- |
| Chord-quality classes | 5: maj7, min7, dom7, m7♭5, dim7 | Folding "dim" into m7♭5 misrepresents the 7th degree for 43 chord events. Extending to a 5th class adds at most 24 theoretical states and preserves harmonic fidelity. |
| Bebop-convention quality recovery | "m" → min7, "" → maj7 | Bare "m" in a 4-note bebop context implies min7; surrounding chord tones confirm 7ths are routinely played over both. |
| Beat-position tolerance | 0.05 quarter-notes | Absorbs grace notes and transcriber rounding without leaking "and"-of-beat eighths into the strong-beat class. |
| Beat-position granularity | **v3: 8 classes (1, 2, 3, 4, &1, &2, &3, &4)** | v1 used binary on/off; v2 split the four downbeats; v3 also splits the offbeat class by the beat it follows, so the pickup (&4) is separable from mid-bar off-beats. The V7→I cell resolves to a single source position (15.29 %) with its neighbours at ~0, and the metric cycle appears in the spectrum of P. Costs 428 observed states instead of 275, and cuts τ_mix(P_within) from 46 to 14. |
| Rest handling | **v2: rests as states with chord context; consecutive rests collapsed** | v1 ignored rests (continuous note streams). v2 captures phrasing structure. Collapsing consecutive rests prevents long-silence dominance of the operator. |
| Beat reference | MusicXML notated offset, not MIDI | Notated beat is what bebop theorists mean by "on the beat". MIDI alignment is per-segment, not per-note; rebuilding it is orthogonal to the model. |
| Smoothing α | 0.01 | Small enough that observed transitions dominate; large enough for Perron-Frobenius irreducibility and `I − Q` invertibility. |
| Within/across split | conditioned on the destination's chord-change flag | A chord change is observed at the destination note. Conditioning on the source mis-classifies the first note of every new chord. |
| Memory-order parameter count | observed cells | n²(n−1) ≈ 5.5M parameters for a 4K-cell observed model is wildly conservative; observed-count BIC penalizes only what the model actually uses. |

---

## Limitations

**Roughly half the model's predictive power is metre, not music.**
Conditional entropy of the next state is 7.80 bits knowing nothing, 5.89
bits knowing only the current beat position, and 3.63 bits knowing the
full state. Of the 4.16 bits the full state buys, 1.91 (**46 %**) is
available from the beat coordinate alone, because 73 % of transitions
advance exactly one eighth and a further 13 % are subdivisions inside one
beat. This is why Section 6 reports a beat-preserving null as well as the
standard one. It also explains the complex λ₂ of P (Section 3): the metric
cycle is a real, dominant mode of the operator.

- 23k events is enough for first-order analysis but marginal for
  second-order (held-out test favors order-1 despite large in-sample
  ΔBIC).
- Quality mapping discards 7th-degree alterations on dominants (alt,
  ♯11, ♭9 all collapse to `dom7`).
- MIDI tempo and swing are ignored — notated beat only.
- No transitions across tune boundaries are counted.
- Rests inherit the active chord at their onset; a rest spanning a
  chord change is attributed to the chord at the start of the silence
  (after collapsing consecutive rests, all rests in a silence run
  share one chord context).
