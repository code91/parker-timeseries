# Robustness checks run in response to Reviewer 1

## 1. Collinearity of complexity and dissonance (R1, major point)

Reviewer 1 was correct, and the dependency is structural, not merely empirical:
dissonance = ic1 + 0.5*ic2 + 0.8*ic6 is a weighted SUB-SUM of complexity = sum(ic1..ic6).

| level | n | Pearson r | r^2 |
|---|---|---|---|
| segment | 3,024 | 0.937 | 0.877 |
| phrase | 1,507 | 0.939 | 0.882 |
| within-tune (46 Granger tunes) | — | mean 0.928 (range 0.814–0.986) | mean 0.863 |

Implied VIF for a two-predictor model: 7.32 (conventional concern threshold 5–10).
All 46 tunes have |r| > 0.7.

## 2. Re-run with a density-independent dissonance measure

Defined dissonance ratio = dissonance / complexity, which removes the density component.
Correlation with complexity drops from r = .939 to **r = .032**.

Granger significance rates (lag 1, p < .05, 46 tunes):

| measure | D->C | C->D | neither | mean F (D->C / C->D) |
|---|---|---|---|---|
| raw dissonance (published) | 8/46 = 17.4% | 4/46 = 8.7% | 37/46 = 80.4% | 2.12 / 1.36 |
| density-independent | 5/46 = 10.9% | 2/46 = 4.3% | 39/46 = 84.8% | 1.77 / 0.90 |

**Conclusions are unchanged and in fact strengthened**: phrase-level causality remains a
minority pattern (84.8% show none, up from 80.4%), and the directional asymmetry
D->C > C->D persists (2.5:1, previously 2:1), with the higher mean F still on D->C.

NOTE: the lag-1 raw-dissonance row reproduces the published numbers exactly
(8/46, 4/46, 37/46, F = 2.12/1.36), confirming the reimplementation is faithful.

## 3. Sensitivity to the dissonance weighting scheme (R1 asked for evidence)

K-means (k=4, 20 restarts, z-scored features) re-run under alternative weightings;
agreement with the published strategy assignment:

| scheme (ic1, ic2, ic6) | ARI | % tunes same strategy |
|---|---|---|
| ic6 = 0.6 (1.0, 0.5, 0.6) | 1.000 | 100.0% |
| ic6 = 1.0 (1.0, 0.5, 1.0) | 0.575 | 82.6% |
| ic2 = 0.25 (1.0, 0.25, 0.8) | 0.549 | 84.8% |
| equal weights (1.0, 1.0, 1.0) | 1.000 | 100.0% |
| + ic4 = 0.2 penalty | 1.000 | 100.0% |

Three of five alternatives reproduce the assignment exactly; the remaining two agree
on 83–85% of tunes.

## 4. Cohen's d vs 95% CI (Reviewer 2 flagged an inconsistency)

Reviewer 2 is right that d = -0.87 lies outside [-2.55, -1.50], but the numbers are
correct and the LABELLING is wrong. 11_robustness.py:387-392 computes that CI for the
**difference in means** (-2.0 triads), not for d. Fix is to report it as such.
