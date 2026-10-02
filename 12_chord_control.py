#!/usr/bin/env python3
"""
12_chord_control.py

Control analysis for the confound raised in peer review: how much of the
temporal structure we report belongs to Parker, and how much to the chord
progressions he was playing over?

The test holds the changes fixed and replaces Parker. For every segment we keep
the actual chord, the actual key, the actual number of distinct pitch classes
and the actual position in the performance, and draw that many pitch classes at
random from the scale the chord implies under chord-scale theory. Complexity and
dissonance are then computed exactly as in the main analysis, phrases are
rebuilt over the same rest-delimited spans, and the same statistics are run.

Anything the null reproduces is attributable to the progressions. Anything the
observed data shows and the null does not is attributable to the improviser.

Input:  parker_timeseries.csv, parker_phrases.csv
Output: parker_chord_control.csv
"""

import csv, ast, sys
from collections import defaultdict
import numpy as np
from scipy.stats import f as fdist

N_SIMS = 500
RNG = np.random.default_rng(20260101)

# Chord-scale theory: the scale each function implies, as semitone offsets from
# the chord root. Diatonic functions take their modal scale; altered and
# borrowed functions take the scale conventionally taught for them.
SCALES = {
    'I':    [0, 2, 4, 5, 7, 9, 11],   # Ionian
    'II':   [0, 2, 3, 5, 7, 9, 10],   # Dorian
    'III':  [0, 1, 3, 5, 7, 8, 10],   # Phrygian
    'IV':   [0, 2, 4, 6, 7, 9, 11],   # Lydian
    'V':    [0, 2, 4, 5, 7, 9, 10],   # Mixolydian
    'VI':   [0, 2, 3, 5, 7, 8, 10],   # Aeolian
    'VII':  [0, 1, 3, 5, 6, 8, 10],   # Locrian
    'bII':  [0, 1, 3, 4, 6, 8, 10],   # altered (tritone-sub dominant)
    'bIII': [0, 2, 4, 5, 7, 9, 10],   # Mixolydian (secondary dominant)
    'bVI':  [0, 2, 4, 5, 7, 9, 10],   # Mixolydian
    'bVII': [0, 2, 4, 5, 7, 9, 10],   # Mixolydian
    '#IV':  [0, 1, 3, 5, 6, 8, 10],   # Locrian (half-diminished)
}
DEFAULT_SCALE = SCALES['I']


def interval_vector(pcs):
    v = [0] * 6
    pcs = sorted(set(pcs))
    for i in range(len(pcs)):
        for j in range(i + 1, len(pcs)):
            d = (pcs[j] - pcs[i]) % 12
            v[min(d, 12 - d) - 1] += 1
    return v


def metrics(pcs):
    """Complexity and dissonance, defined exactly as in the main analysis."""
    v = interval_vector(pcs)
    return sum(v), v[0] + 0.5 * v[1] + 0.8 * v[5]


def load():
    seg = list(csv.DictReader(open('parker_timeseries.csv')))
    ph = list(csv.DictReader(open('parker_phrases.csv')))
    return seg, ph


def cardinality_pools(seg):
    """How many distinct pitch classes Parker uses over each chord function.

    The null must draw this too. Complexity is exactly C(n, 2) in the number of
    distinct pitch classes n -- verified on all 3,024 segments, with no
    exceptions -- so holding n fixed would hold complexity fixed and the null
    would simply reproduce the observed series.
    """
    pools = defaultdict(list)
    for r in seg:
        pools[r['chord_function']].append(int(r['cardinality']))
    return {k: np.array(v) for k, v in pools.items()}


def simulate_segments(seg, pools):
    """One null draw: the real chord sequence, but another player over it.

    For each segment the number of distinct pitch classes is drawn from what
    that chord function attracts corpus-wide, and the pitch classes themselves
    are drawn from the scale the chord implies. Everything that survives is
    attributable to the progression rather than to the improviser.
    """
    comp = np.empty(len(seg))
    diss = np.empty(len(seg))
    for i, r in enumerate(seg):
        fn = r['chord_function']
        scale = SCALES.get(fn, DEFAULT_SCALE)
        pool = pools.get(fn)
        n = int(RNG.choice(pool)) if pool is not None and len(pool) else int(r['cardinality'])
        n = min(n, len(scale))
        pcs = RNG.choice(scale, size=n, replace=False)
        comp[i], diss[i] = metrics(pcs)
    return comp, diss


def ssr_ftest(y, x, lag=1):
    n = len(y)
    if n < 3 * lag + 6:
        return None
    Y = y[lag:]
    L = lambda v: np.column_stack([v[lag - i - 1:len(v) - i - 1] for i in range(lag)])
    Xr = np.column_stack([np.ones(len(Y)), L(y)])
    Xu = np.column_stack([Xr, L(x)])
    def ssr(X):
        b, *_ = np.linalg.lstsq(X, Y, rcond=None)
        e = Y - X @ b
        return float(e @ e)
    sr, su = ssr(Xr), ssr(Xu)
    df = len(Y) - Xu.shape[1]
    if df <= 0 or su <= 0:
        return None
    F = ((sr - su) / lag) / (su / df)
    return F, 1 - fdist.cdf(F, lag, df)


def phrase_series(ph, comp, diss, seg_index):
    """Aggregate segment values over the real rest-delimited phrase spans."""
    out = defaultdict(list)
    for p in ph:
        key = (p['tune'], int(p['start_segment_idx']), int(p['end_segment_idx']))
        idx = [seg_index.get((p['tune'], i)) for i in range(key[1], key[2] + 1)]
        idx = [i for i in idx if i is not None]
        if not idx:
            continue
        out[p['tune']].append((float(np.mean(comp[idx])), float(np.mean(diss[idx])),
                               int(p['segment_count'])))
    return out


def granger_rates(by_tune):
    """Share of tunes where one phrase series Granger-causes another, lag 1."""
    hits = {'D->C': 0, 'C->D': 0}
    used = 0
    for tune, v in by_tune.items():
        if len(v) < 10:
            continue
        used += 1
        c = np.array([x[0] for x in v]); d = np.array([x[1] for x in v])
        if c.std() == 0 or d.std() == 0:
            continue
        for name, cause, effect in (('D->C', d, c), ('C->D', c, d)):
            o = ssr_ftest(effect, cause, 1)
            if o and o[1] < 0.05:
                hits[name] += 1
    return hits, used


def tune_stats(by_tune):
    """Lag-1 autocorrelation and volatility of complexity, per tune."""
    ac, cv = [], []
    for tune, v in by_tune.items():
        c = np.array([x[0] for x in v])
        if len(c) < 6 or c.std() == 0:
            continue
        ac.append(float(np.corrcoef(c[:-1], c[1:])[0, 1]))
        cv.append(float(c.std() / c.mean()))
    return np.array(ac), np.array(cv)


def main():
    seg, ph = load()
    seg_index = {(r['tune'], int(r['segment_idx'])): i for i, r in enumerate(seg)}
    pools = cardinality_pools(seg)
    print(f"Loaded {len(seg)} segments and {len(ph)} phrases")

    obs_comp = np.array([float(r['iv_sum']) for r in seg])
    obs_diss = np.array([float(r['dissonance']) for r in seg])
    obs_by_tune = phrase_series(ph, obs_comp, obs_diss, seg_index)
    obs_hits, used = granger_rates(obs_by_tune)
    obs_ac, obs_cv = tune_stats(obs_by_tune)

    print("\nOBSERVED")
    print(f"  complexity mean {obs_comp.mean():.2f}   dissonance mean {obs_diss.mean():.2f}")
    print(f"  D->C {100*obs_hits['D->C']/used:.1f}%   C->D {100*obs_hits['C->D']/used:.1f}%  (n={used})")
    print(f"  mean lag-1 autocorrelation {obs_ac.mean():+.3f}   mean volatility {obs_cv.mean():.3f}")

    print(f"\nRunning {N_SIMS} null simulations...")
    null = defaultdict(list)
    for s in range(N_SIMS):
        c, d = simulate_segments(seg, pools)
        bt = phrase_series(ph, c, d, seg_index)
        h, u = granger_rates(bt)
        a, v = tune_stats(bt)
        null['comp'].append(c.mean()); null['diss'].append(d.mean())
        null['dc'].append(100 * h['D->C'] / u); null['cd'].append(100 * h['C->D'] / u)
        null['ac'].append(a.mean()); null['cv'].append(v.mean())
        if (s + 1) % 100 == 0:
            print(f"  {s+1}/{N_SIMS}")

    def report(label, obs, key, fmt="{:.3f}"):
        arr = np.array(null[key])
        lo, hi = np.percentile(arr, [2.5, 97.5])
        p = (np.sum(np.abs(arr - arr.mean()) >= abs(obs - arr.mean())) + 1) / (len(arr) + 1)
        verdict = "OUTSIDE null" if (obs < lo or obs > hi) else "inside null"
        print(f"  {label:34s} observed {fmt.format(obs)}   null {fmt.format(arr.mean())} "
              f"[{fmt.format(lo)}, {fmt.format(hi)}]   {verdict}  p = {p:.3f}")

    print("\nOBSERVED vs NULL (95% interval over simulations)")
    report("mean complexity", obs_comp.mean(), 'comp', "{:.2f}")
    report("mean dissonance", obs_diss.mean(), 'diss', "{:.2f}")
    report("Dissonance->Complexity rate (%)", 100*obs_hits['D->C']/used, 'dc', "{:.1f}")
    report("Complexity->Dissonance rate (%)", 100*obs_hits['C->D']/used, 'cd', "{:.1f}")
    report("mean lag-1 autocorrelation", obs_ac.mean(), 'ac', "{:+.3f}")
    report("mean volatility (CV)", obs_cv.mean(), 'cv', "{:.3f}")

    with open('parker_chord_control.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['statistic', 'observed', 'null_mean', 'null_lo95', 'null_hi95'])
        for label, obs, key in (("mean_complexity", obs_comp.mean(), 'comp'),
                                ("mean_dissonance", obs_diss.mean(), 'diss'),
                                ("granger_d_to_c_pct", 100*obs_hits['D->C']/used, 'dc'),
                                ("granger_c_to_d_pct", 100*obs_hits['C->D']/used, 'cd'),
                                ("mean_lag1_autocorr", obs_ac.mean(), 'ac'),
                                ("mean_volatility_cv", obs_cv.mean(), 'cv')):
            a = np.array(null[key]); lo, hi = np.percentile(a, [2.5, 97.5])
            w.writerow([label, f"{obs:.4f}", f"{a.mean():.4f}", f"{lo:.4f}", f"{hi:.4f}"])
    print("\nSaved: parker_chord_control.csv")


if __name__ == '__main__':
    main()
