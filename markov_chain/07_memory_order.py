"""
Section 7 — Memory order (1 vs 2).

A first-order Markov chain assigns Pr(X_{t+1} | X_t).  A second-order chain
treats the state as the pair (X_{t-1}, X_t) and assigns
    Pr(X_{t+1} | X_t, X_{t-1}).
The question is whether melodic continuation depends on more than just the
current note.  Parker's bebop language is famous for enclosure figures and
double-chromatic approaches — multi-note shapes that span 2–3 notes.  So
we predict:
    - order-1 is adequate for P̂_within (single-note context captures the
      local melodic logic)
    - order-2 is meaningfully better for P̂_across (enclosure and
      double-chromatic patterns span the chord boundary)

Estimation.  Laplace smoothing α = SMOOTHING_ALPHA on each row of the
order-2 count matrix.  For test contexts unseen in training we BACK OFF
to the order-1 model — a standard NLP technique that avoids collapsing
unseen pair-states to a uniform 1/n.

Model comparison.
    AIC = 2k - 2 log L_train,   BIC = k log T - 2 log L_train.
We report parameter counts in TWO ways:
    k_max  = n × (n-1)   for order-1,   n² × (n-1) for order-2.
    k_obs  = #observed cells - #observed contexts
            (only contexts actually used cost parameters).
The k_obs version is more honest for sparse data.  Both are reported.
Positive ΔBIC = BIC_1 - BIC_2 means order-2 is preferred.

Train/test split.  Per tune, the first 80% of transitions train, the last
20% test.  Reported metric: total test log-likelihood and per-transition
mean log-likelihood for each model.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from markov_chain.common import (  # noqa: E402
    DATA_DIR,
    FIGURES_DIR,
    SMOOTHING_ALPHA,
    load_notes,
    load_state_order,
    state_index_map,
)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "savefig.dpi": 300,
})

TRAIN_FRAC = 0.8


def collect_transitions(df, idx: dict) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """For each tune return (tune_id, state_indices, chord_changed_flags)."""
    out = []
    for tune_id, grp in df.groupby("tune_id", sort=False):
        states = [idx[s] for s in grp["state"]]
        changed = np.array(grp["chord_changed_from_prev"].tolist(), dtype=bool)
        out.append((tune_id, np.array(states, dtype=np.int64), changed))
    return out


def split_train_test_pairs(per_tune: list, kind: str, train_frac: float):
    """Yield (train_pairs, test_pairs, train_triples, test_triples) for the given kind.

    A pair is (X_t, X_{t+1}); a triple is (X_{t-1}, X_t, X_{t+1}).  Pairs/triples are
    only emitted at positions where the chord-change condition matches `kind`.
    """
    train_pairs, test_pairs = [], []
    train_triples, test_triples = [], []
    for _, states, changed in per_tune:
        n_trans = len(states) - 1
        if n_trans <= 0:
            continue
        n_train = max(1, int(round(n_trans * train_frac)))
        for t in range(n_trans):
            use = (kind == "all") or \
                  (kind == "within" and not changed[t + 1]) or \
                  (kind == "across" and changed[t + 1])
            if not use:
                continue
            pair = (int(states[t]), int(states[t + 1]))
            (train_pairs if t < n_train else test_pairs).append(pair)
            if t >= 1:
                triple = (int(states[t - 1]), int(states[t]), int(states[t + 1]))
                (train_triples if t < n_train else test_triples).append(triple)
    return train_pairs, test_pairs, train_triples, test_triples


def fit_order1(pairs: list[tuple[int, int]], n: int, alpha: float):
    """Return smoothed P (n x n) and raw row sums."""
    N = np.zeros((n, n), dtype=np.int64)
    for i, j in pairs:
        N[i, j] += 1
    P = N.astype(np.float64) + alpha
    P /= P.sum(axis=1, keepdims=True)
    return P, N


def fit_order2(triples: list[tuple[int, int, int]], n: int, alpha: float):
    """Return dict: (i,j) -> smoothed row over k, plus context counts."""
    counts: dict[tuple[int, int], np.ndarray] = defaultdict(lambda: np.zeros(n, dtype=np.int64))
    for i, j, k in triples:
        counts[(i, j)][k] += 1
    rows: dict[tuple[int, int], np.ndarray] = {}
    context_counts: dict[tuple[int, int], int] = {}
    for ctx, row in counts.items():
        smoothed = row.astype(np.float64) + alpha
        rows[ctx] = smoothed / smoothed.sum()
        context_counts[ctx] = int(row.sum())
    return rows, context_counts


def log_likelihood_order1(pairs: list[tuple[int, int]], P: np.ndarray) -> float:
    if not pairs:
        return 0.0
    return float(sum(math.log(P[i, j]) for i, j in pairs))


def log_likelihood_order2(
    triples: list[tuple[int, int, int]],
    P2: dict[tuple[int, int], np.ndarray],
    P1: np.ndarray,
) -> tuple[float, int, int]:
    """Return (log L, n_used_order2, n_backoff_order1)."""
    ll = 0.0
    n_o2 = 0
    n_bo = 0
    for i, j, k in triples:
        if (i, j) in P2:
            ll += math.log(P2[(i, j)][k])
            n_o2 += 1
        else:
            ll += math.log(P1[j, k])  # back off to order-1
            n_bo += 1
    return ll, n_o2, n_bo


def observed_param_count_order1(N: np.ndarray) -> int:
    """#observed cells - #observed rows."""
    cells = int((N > 0).sum())
    rows = int((N.sum(axis=1) > 0).sum())
    return max(cells - rows, 0)


def observed_param_count_order2(context_counts: dict[tuple[int, int], int],
                                counts: dict[tuple[int, int], np.ndarray]) -> int:
    cells = 0
    contexts = 0
    for ctx, row in counts.items():
        positive = int((row > 0).sum())
        if positive > 0:
            cells += positive
            contexts += 1
    return max(cells - contexts, 0)


def main() -> None:
    states = load_state_order()
    idx = state_index_map(states)
    n = len(states)

    df = load_notes()
    per_tune = collect_transitions(df, idx)

    summary: dict = {}
    for kind in ("all",):
        train_pairs, test_pairs, train_triples, test_triples = split_train_test_pairs(
            per_tune, kind, TRAIN_FRAC
        )
        if not train_pairs or not test_pairs:
            continue

        P1_train, N1_train = fit_order1(train_pairs, n, SMOOTHING_ALPHA)
        P2_train, ctx_counts = fit_order2(train_triples, n, SMOOTHING_ALPHA)

        ll1_train = log_likelihood_order1(train_pairs, P1_train)
        ll1_test = log_likelihood_order1(test_pairs, P1_train)

        # Order-2 LL on the *same* test events (pairs ↔ triples) for fair comparison.
        # Build triples for test_pairs by re-walking the per-tune sequence and picking the
        # same positions; simpler: just use the explicitly stored test_triples (which
        # already match positions t >= 1 of the test split).  Order-1 LL is computed on
        # test_pairs for that purpose; for fair comparison we restrict order-1 LL to the
        # same positions as the triples (i.e. positions t >= 1).
        # Map: test_triples[m] = (i, j, k) corresponds to a transition (j -> k); we want
        # the same set under the order-1 model.
        test_pairs_for_triples = [(j, k) for (_, j, k) in test_triples]
        ll1_test_aligned = log_likelihood_order1(test_pairs_for_triples, P1_train)
        ll2_test, n_o2, n_bo = log_likelihood_order2(test_triples, P2_train, P1_train)

        T_train = len(train_pairs)
        # AIC / BIC computed on training LL with TWO parameter-count conventions.
        # 1. Theoretical max.
        k1_max = n * (n - 1)
        k2_max = (n * n) * (n - 1)
        # 2. Observed cells (more honest for sparse data).
        # Need triple-count matrix for observed param count on order-2 — reconstruct.
        triple_counts: dict[tuple[int, int], np.ndarray] = defaultdict(lambda: np.zeros(n, dtype=np.int64))
        for i, j, k in train_triples:
            triple_counts[(i, j)][k] += 1
        k1_obs = observed_param_count_order1(N1_train)
        k2_obs = observed_param_count_order2(ctx_counts, triple_counts)

        # Need order-2 training LL for AIC/BIC at order-2.
        ll2_train, _, _ = log_likelihood_order2(train_triples, P2_train, P1_train)

        def aic(ll, k): return 2 * k - 2 * ll
        def bic(ll, k, T): return k * math.log(T) - 2 * ll

        aic1_max = aic(ll1_train, k1_max);   aic2_max = aic(ll2_train, k2_max)
        aic1_obs = aic(ll1_train, k1_obs);   aic2_obs = aic(ll2_train, k2_obs)
        bic1_max = bic(ll1_train, k1_max, T_train); bic2_max = bic(ll2_train, k2_max, T_train)
        bic1_obs = bic(ll1_train, k1_obs, T_train); bic2_obs = bic(ll2_train, k2_obs, T_train)

        # Held-out per-transition mean LL
        mean_ll1 = ll1_test_aligned / max(len(test_triples), 1)
        mean_ll2 = ll2_test / max(len(test_triples), 1)

        op_name = "P" if kind == "all" else f"P_{kind}"
        print(f"\n--- {op_name} ---")
        print(f"  train transitions   : {T_train:,}    test transitions = {len(test_pairs):,}")
        print(f"  train triples       : {len(train_triples):,}    test triples = {len(test_triples):,}")
        print(f"  k_max  (order1, order2)  : {k1_max:,}   {k2_max:,}")
        print(f"  k_obs  (order1, order2)  : {k1_obs:,}   {k2_obs:,}")
        print(f"  ΔAIC (max-params)  = AIC1 - AIC2 = {aic1_max - aic2_max:+.1f}   "
              f"(positive: order-2 wins)")
        print(f"  ΔBIC (max-params)  = BIC1 - BIC2 = {bic1_max - bic2_max:+.1f}")
        print(f"  ΔAIC (obs-params)  = {aic1_obs - aic2_obs:+.1f}")
        print(f"  ΔBIC (obs-params)  = {bic1_obs - bic2_obs:+.1f}")
        print(f"  held-out mean log-likelihood:  order-1 = {mean_ll1:.4f}   order-2 = {mean_ll2:.4f}")
        print(f"  held-out delta (o2 - o1)     :  {mean_ll2 - mean_ll1:+.4f}  nats/transition")
        print(f"  order-2 lookups using stored context : {n_o2:,}    backoff to order-1 : {n_bo:,}")

        summary[op_name] = {
            "T_train": T_train,
            "T_test": len(test_pairs),
            "n_triples_train": len(train_triples),
            "n_triples_test": len(test_triples),
            "ll1_train": ll1_train,
            "ll2_train": ll2_train,
            "ll1_test_aligned": ll1_test_aligned,
            "ll2_test": ll2_test,
            "test_mean_ll_order1": mean_ll1,
            "test_mean_ll_order2": mean_ll2,
            "test_mean_ll_delta": mean_ll2 - mean_ll1,
            "k1_max": k1_max,
            "k2_max": k2_max,
            "k1_obs": k1_obs,
            "k2_obs": k2_obs,
            "delta_AIC_max": aic1_max - aic2_max,
            "delta_BIC_max": bic1_max - bic2_max,
            "delta_AIC_obs": aic1_obs - aic2_obs,
            "delta_BIC_obs": bic1_obs - bic2_obs,
            "test_lookups_order2": n_o2,
            "test_lookups_backoff": n_bo,
        }

    with (DATA_DIR / "section7_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    # Comparison figure: held-out per-transition mean log-likelihood, order 1 vs order 2
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    names = list(summary.keys())
    ll1 = [summary[n]["test_mean_ll_order1"] for n in names]
    ll2 = [summary[n]["test_mean_ll_order2"] for n in names]
    x = np.arange(len(names))
    w = 0.36
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.bar(x - w/2, ll1, w, label="order-1", color="#3b6fb6", edgecolor="black", linewidth=0.3)
    ax.bar(x + w/2, ll2, w, label="order-2 (backoff)", color="#c0392b", edgecolor="black", linewidth=0.3)
    ax.set_xticks(x); ax.set_xticklabels(names)
    ax.set_ylabel("held-out mean log-likelihood  (nats / transition)")
    ax.set_title("Section 7: held-out predictive log-likelihood, order-1 vs order-2")
    ax.axhline(0, color="grey", linewidth=0.4)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "section7_heldout_ll.png")
    fig.savefig(FIGURES_DIR / "section7_heldout_ll.pdf")
    plt.close(fig)

    # And ΔBIC chart (observed-param convention)
    dbic = [summary[n]["delta_BIC_obs"] for n in names]
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    colors = ["#3b6fb6" if d <= 0 else "#c0392b" for d in dbic]
    ax.bar(x, dbic, color=colors, edgecolor="black", linewidth=0.3)
    ax.set_xticks(x); ax.set_xticklabels(names)
    ax.set_ylabel("ΔBIC = BIC(order-1) − BIC(order-2)   [obs-params]")
    ax.set_title("Section 7: in-sample ΔBIC  (positive: order-2 preferred)")
    ax.axhline(0, color="grey", linewidth=0.4)
    for xi, di in zip(x, dbic):
        ax.text(xi, di + (max(dbic) * 0.02), f"{di:+.0f}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "section7_delta_bic.png")
    fig.savefig(FIGURES_DIR / "section7_delta_bic.pdf")
    plt.close(fig)

    print(f"\nWrote section7_summary.json and figures")


if __name__ == "__main__":
    main()
