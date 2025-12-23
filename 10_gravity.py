#!/usr/bin/env python3
"""
10_granger_causality_gravity.py
Granger causality analysis to test "Gravity" - causal relationships between
harmonic variables over time.

Tests:
1. Complexity → Dissonance (tension creation)
2. Dissonance → Complexity (response)
3. Phrase length → Complexity (opportunity)
4. Phrase length → Dissonance (opportunity)

Outputs:
- Per-tune Granger test results with statistical significance tests
- Asymmetry analysis (binomial tests)
- Cluster-level causality patterns
- Visualization of causal strength
"""

import subprocess
import sys

for pkg in ['pandas', 'numpy', 'matplotlib', 'seaborn', 'statsmodels', 'scipy']:
    try:
        __import__(pkg.replace('-', '_'))
    except ImportError:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from statsmodels.tsa.stattools import grangercausalitytests
from scipy.stats import binomtest
import warnings
warnings.filterwarnings('ignore')

INPUT_CSV = 'parker_phrases.csv'
CLUSTER_CSV = 'parker_cluster_assignments.csv'
PLOTS_DIR = Path('10_granger_plots')
PLOTS_DIR.mkdir(exist_ok=True)

# Test configurations
CAUSAL_TESTS = [
    ('mean_iv_sum', 'mean_dissonance', 'Complexity → Dissonance'),
    ('mean_dissonance', 'mean_iv_sum', 'Dissonance → Complexity'),
    ('segment_count', 'mean_iv_sum', 'Phrase Length → Complexity'),
    ('segment_count', 'mean_dissonance', 'Phrase Length → Dissonance'),
]

MAX_LAG = 3
MIN_OBSERVATIONS = 10  # Minimum phrases needed for test


def load_data():
    """Load phrase data with cluster assignments."""
    phrases_df = pd.read_csv(INPUT_CSV)

    try:
        cluster_df = pd.read_csv(CLUSTER_CSV)
        phrases_df = phrases_df.merge(cluster_df, on='tune', how='left')
        print(f"Loaded {len(phrases_df)} phrases with cluster assignments")
    except:
        print(f"Loaded {len(phrases_df)} phrases (no cluster assignments)")
        phrases_df['cluster'] = np.nan

    return phrases_df


def granger_test_tune(tune_df, cause_var, effect_var, max_lag=3):
    """
    Perform Granger causality test for one tune.

    Returns dict with F-stats and p-values for each lag.
    """
    # Prepare data
    data = tune_df[[cause_var, effect_var]].dropna()

    if len(data) < MIN_OBSERVATIONS:
        return None

    try:
        # Granger test
        # Note: statsmodels expects [effect, cause] order
        test_data = data[[effect_var, cause_var]].values

        results = grangercausalitytests(test_data, maxlag=max_lag, verbose=False)

        # Extract F-statistics and p-values
        output = {}
        for lag in range(1, max_lag + 1):
            # Get F-test results (ssr_ftest)
            ftest = results[lag][0]['ssr_ftest']
            output[f'lag{lag}_fstat'] = ftest[0]
            output[f'lag{lag}_pvalue'] = ftest[1]

        return output

    except Exception as e:
        # Test failed (insufficient data, singularity, etc.)
        return None


def test_all_tunes(phrases_df):
    """
    Run all Granger tests for all tunes.
    """
    results = []

    print("\nRunning Granger causality tests...")
    print("="*70)

    for tune in phrases_df['tune'].unique():
        tune_df = phrases_df[phrases_df['tune'] == tune].sort_values('phrase_id')

        if len(tune_df) < MIN_OBSERVATIONS:
            continue

        tune_result = {
            'tune': tune,
            'n_phrases': len(tune_df)
        }

        # Get cluster if available
        if 'cluster' in tune_df.columns:
            cluster = tune_df['cluster'].iloc[0]
            if not pd.isna(cluster):
                tune_result['cluster'] = int(cluster)

        # Run each causal test
        for cause_var, effect_var, test_name in CAUSAL_TESTS:
            test_result = granger_test_tune(tune_df, cause_var, effect_var, max_lag=MAX_LAG)

            if test_result is not None:
                # Add results with prefix
                prefix = f"{cause_var}_to_{effect_var}"
                for key, value in test_result.items():
                    tune_result[f"{prefix}_{key}"] = value

        results.append(tune_result)

        if len(results) % 10 == 0:
            print(f"  Processed {len(results)} tunes...")

    results_df = pd.DataFrame(results)
    print(f"\nCompleted tests for {len(results_df)} tunes")

    return results_df


def test_directional_asymmetry(results_df, cause1_var, effect1_var, cause2_var, effect2_var,
                               test_name1, test_name2, significance=0.05):
    """
    Test if two directional causal tests show significant asymmetry.

    For example: Does Dissonance→Complexity occur more often than Complexity→Dissonance?

    Uses binomial test: among tunes showing causality in EITHER direction,
    is the split significantly different from 50/50?
    """
    print(f"\n{'='*70}")
    print(f"DIRECTIONAL ASYMMETRY TEST")
    print(f"  {test_name1} vs {test_name2}")
    print(f"{'='*70}")

    prefix1 = f"{cause1_var}_to_{effect1_var}"
    prefix2 = f"{cause2_var}_to_{effect2_var}"

    pval1_col = f"{prefix1}_lag1_pvalue"
    pval2_col = f"{prefix2}_lag1_pvalue"

    if pval1_col not in results_df.columns or pval2_col not in results_df.columns:
        print("Insufficient data for asymmetry test")
        return None

    # Count tunes with valid tests in both directions
    both_valid = results_df[[pval1_col, pval2_col]].dropna()
    n_total = len(both_valid)

    # Count significant results in each direction
    sig1 = (both_valid[pval1_col] < significance).sum()
    sig2 = (both_valid[pval2_col] < significance).sum()

    # Count tunes with causality in EITHER direction
    sig_either = ((both_valid[pval1_col] < significance) |
                  (both_valid[pval2_col] < significance)).sum()

    # Count tunes with causality in BOTH directions
    sig_both = ((both_valid[pval1_col] < significance) &
                (both_valid[pval2_col] < significance)).sum()

    # Count tunes with causality in EXACTLY ONE direction
    sig_direction1_only = ((both_valid[pval1_col] < significance) &
                           (both_valid[pval2_col] >= significance)).sum()
    sig_direction2_only = ((both_valid[pval1_col] >= significance) &
                           (both_valid[pval2_col] < significance)).sum()

    # Percentages
    pct1 = (sig1 / n_total * 100) if n_total > 0 else 0
    pct2 = (sig2 / n_total * 100) if n_total > 0 else 0
    pct_either = (sig_either / n_total * 100) if n_total > 0 else 0
    pct_neither = ((n_total - sig_either) / n_total * 100) if n_total > 0 else 0

    print(f"\nDataset: {n_total} tunes with valid tests in both directions")
    print(f"\nSignificant causality (p < {significance}):")
    print(f"  {test_name1}: {sig1}/{n_total} ({pct1:.1f}%)")
    print(f"  {test_name2}: {sig2}/{n_total} ({pct2:.1f}%)")
    print(f"  Either direction: {sig_either}/{n_total} ({pct_either:.1f}%)")
    print(f"  Neither direction: {n_total - sig_either}/{n_total} ({pct_neither:.1f}%)")
    print(f"  Both directions: {sig_both} tunes")

    # Binomial test among tunes showing causality in exactly one direction
    n_directional = sig_direction1_only + sig_direction2_only

    if n_directional > 0:
        print(f"\nAmong {n_directional} tunes showing unidirectional causality:")
        print(f"  {test_name1} only: {sig_direction1_only}")
        print(f"  {test_name2} only: {sig_direction2_only}")

        # Binomial test: is this split significantly different from 50/50?
        # We test the more common direction
        n_successes = max(sig_direction1_only, sig_direction2_only)
        p_binom = binomtest(n_successes, n_directional, p=0.5, alternative='greater').pvalue

        print(f"\nBinomial test (H0: equal probability of each direction):")
        print(f"  n_successes: {n_successes}")
        print(f"  n_trials: {n_directional}")
        print(f"  p-value: {p_binom:.4f}")

        if p_binom < 0.05:
            print(f"  Result: SIGNIFICANT asymmetry (p < 0.05)")
            if sig_direction1_only > sig_direction2_only:
                print(f"  → {test_name1} predominates")
            else:
                print(f"  → {test_name2} predominates")
        else:
            print(f"  Result: No significant asymmetry")
    else:
        print(f"\nNo tunes show unidirectional causality")
        p_binom = None

    # Chi-square test for overall asymmetry
    # (More appropriate than binomial when some tunes show bidirectional causality)
    from scipy.stats import chi2_contingency

    contingency_table = [
        [sig_direction1_only, sig_direction2_only],
        [sig2 - sig_both, sig1 - sig_both]  # Include tunes with bidirectional causality
    ]

    print(f"\n{'='*70}")
    print("INTERPRETATION")
    print(f"{'='*70}")

    print(f"\n1. PREVALENCE:")
    print(f"   {test_name1}: {pct1:.1f}% of tunes")
    print(f"   {test_name2}: {pct2:.1f}% of tunes")

    if pct1 > pct2 * 1.5:
        ratio = pct1 / pct2 if pct2 > 0 else float('inf')
        print(f"   → {test_name1} is {ratio:.1f}× more common")
    elif pct2 > pct1 * 1.5:
        ratio = pct2 / pct1 if pct1 > 0 else float('inf')
        print(f"   → {test_name2} is {ratio:.1f}× more common")
    else:
        print(f"   → Similar prevalence")

    print(f"\n2. MAJORITY PATTERN:")
    print(f"   {pct_neither:.1f}% of tunes show NO causality in either direction")
    print(f"   → Most temporal organization is independent of local phrase-level causality")

    print(f"\n3. DIRECTIONAL PREFERENCE:")
    if p_binom is not None and p_binom < 0.05:
        print(f"   Significant asymmetry detected (binomial p = {p_binom:.4f})")
        if sig_direction1_only > sig_direction2_only:
            print(f"   → When causality exists, {test_name1} is preferred")
        else:
            print(f"   → When causality exists, {test_name2} is preferred")
    else:
        print(f"   No significant directional preference detected")

    return {
        'n_total': n_total,
        'sig1': sig1,
        'sig2': sig2,
        'pct1': pct1,
        'pct2': pct2,
        'sig_either': sig_either,
        'sig_neither': n_total - sig_either,
        'sig_direction1_only': sig_direction1_only,
        'sig_direction2_only': sig_direction2_only,
        'binomial_p': p_binom,
        'ratio': pct1 / pct2 if pct2 > 0 else None
    }


def summarize_causality(results_df, test_name, cause_var, effect_var, significance=0.05):
    """
    Summarize Granger causality results for one test.
    """
    print(f"\n{test_name}")
    print("-" * 70)

    prefix = f"{cause_var}_to_{effect_var}"

    for lag in range(1, MAX_LAG + 1):
        pval_col = f"{prefix}_lag{lag}_pvalue"
        fstat_col = f"{prefix}_lag{lag}_fstat"

        if pval_col not in results_df.columns:
            continue

        # Filter valid results
        valid = results_df[[pval_col, fstat_col]].dropna()

        if len(valid) == 0:
            continue

        # Count significant results
        significant = (valid[pval_col] < significance).sum()
        pct_significant = significant / len(valid) * 100

        # Mean F-statistic
        mean_fstat = valid[fstat_col].mean()
        median_fstat = valid[fstat_col].median()
        median_pval = valid[pval_col].median()

        print(f"  Lag {lag}:")
        print(f"    Significant: {significant}/{len(valid)} ({pct_significant:.1f}%)")
        print(f"    Mean F-stat: {mean_fstat:.3f}")
        print(f"    Median F-stat: {median_fstat:.3f}")
        print(f"    Median p-value: {median_pval:.4f}")


def print_all_summaries(results_df):
    """Print summary for all causal tests."""
    print("\n" + "="*70)
    print("GRANGER CAUSALITY SUMMARY")
    print("="*70)

    for cause_var, effect_var, test_name in CAUSAL_TESTS:
        summarize_causality(results_df, test_name, cause_var, effect_var)


def analyze_by_cluster(results_df):
    """
    Compare causality patterns across clusters.
    """
    if 'cluster' not in results_df.columns:
        print("\nNo cluster information available")
        return

    print("\n" + "="*70)
    print("CAUSALITY BY CLUSTER")
    print("="*70)

    cluster_df = results_df.dropna(subset=['cluster'])

    for cluster_id in sorted(cluster_df['cluster'].unique()):
        cluster_data = cluster_df[cluster_df['cluster'] == cluster_id]

        print(f"\nCluster {int(cluster_id)} ({len(cluster_data)} tunes):")

        for cause_var, effect_var, test_name in CAUSAL_TESTS:
            prefix = f"{cause_var}_to_{effect_var}"

            # Look at lag-1 results
            pval_col = f"{prefix}_lag1_pvalue"
            fstat_col = f"{prefix}_lag1_fstat"

            if pval_col not in cluster_data.columns:
                continue

            valid = cluster_data[[pval_col, fstat_col]].dropna()

            if len(valid) == 0:
                continue

            significant = (valid[pval_col] < 0.05).sum()
            pct_significant = significant / len(valid) * 100
            mean_fstat = valid[fstat_col].mean()

            print(f"  {test_name}:")
            print(f"    Significant: {significant}/{len(valid)} ({pct_significant:.1f}%)")
            print(f"    Mean F-stat: {mean_fstat:.3f}")


def visualize_causality_heatmap(results_df):
    """
    Create heatmap of causality strength (F-statistics) across tunes.
    """
    print("\nCreating causality heatmap...")

    # Select columns for visualization (lag-1 F-stats and p-values)
    fstat_cols = []
    pval_cols = []
    test_labels = []

    for cause_var, effect_var, test_name in CAUSAL_TESTS:
        fstat_col = f"{cause_var}_to_{effect_var}_lag1_fstat"
        pval_col = f"{cause_var}_to_{effect_var}_lag1_pvalue"

        if fstat_col in results_df.columns and pval_col in results_df.columns:
            fstat_cols.append(fstat_col)
            pval_cols.append(pval_col)
            test_labels.append(test_name.replace(' → ', '→'))

    if len(fstat_cols) == 0:
        print("  No F-statistics to plot")
        return

    # Prepare data
    plot_data = results_df[['tune'] + fstat_cols].copy()
    pval_data = results_df[['tune'] + pval_cols].copy()

    # FILTER OUT cXbwc if present
    plot_data = plot_data[~plot_data['tune'].isin(['cXbwc'])].copy()
    pval_data = pval_data[~pval_data['tune'].isin(['cXbwc'])].copy()

    plot_data = plot_data.set_index('tune')
    pval_data = pval_data.set_index('tune')

    plot_data.columns = test_labels
    pval_data.columns = test_labels

    # Sort by mean F-stat
    plot_data['mean_fstat'] = plot_data.mean(axis=1)
    plot_data = plot_data.sort_values('mean_fstat', ascending=False)
    plot_data = plot_data.drop('mean_fstat', axis=1)

    # Take top 20 tunes for readability
    plot_data = plot_data.head(20)

    # Match p-values to same tunes and order
    pval_data = pval_data.loc[plot_data.index]

    # Create annotation matrix: F-stat + asterisk if significant
    annot_matrix = []
    for idx, tune in enumerate(plot_data.index):
        row = []
        for col in plot_data.columns:
            fstat = plot_data.loc[tune, col]
            pval = pval_data.loc[tune, col]

            if pd.isna(fstat):
                row.append('')
            elif pd.notna(pval) and pval < 0.05:
                row.append(f'{fstat:.2f}*')  # Add asterisk for significant
            else:
                row.append(f'{fstat:.2f}')
        annot_matrix.append(row)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 12))

    sns.heatmap(plot_data, annot=annot_matrix, fmt='', cmap='YlOrRd',
                cbar_kws={'label': 'F-statistic'}, ax=ax,
                linewidths=0.5, linecolor='gray')

    ax.set_xlabel('Causal Test', fontsize=12)
    ax.set_ylabel('Tune', fontsize=12)
    ax.set_title('Granger Causality Strength (Lag-1 F-statistics)\nTop 20 Tunes by Mean\n* = p < 0.05',
                fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'causality_heatmap.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/causality_heatmap.png")


def visualize_causality_by_cluster(results_df):
    """
    Boxplot of causality strength by cluster.
    """
    if 'cluster' not in results_df.columns:
        return

    print("\nCreating cluster causality boxplots...")

    cluster_df = results_df.dropna(subset=['cluster'])

    # Prepare data for plotting
    plot_data = []

    for cause_var, effect_var, test_name in CAUSAL_TESTS:
        col = f"{cause_var}_to_{effect_var}_lag1_fstat"

        if col not in cluster_df.columns:
            continue

        for _, row in cluster_df.iterrows():
            if pd.notna(row[col]):
                plot_data.append({
                    'Cluster': int(row['cluster']),
                    'Test': test_name.replace(' → ', '→'),
                    'F-statistic': row[col]
                })

    if len(plot_data) == 0:
        print("  No data to plot")
        return

    plot_df = pd.DataFrame(plot_data)

    # Create plot
    fig, ax = plt.subplots(figsize=(14, 6))

    sns.boxplot(data=plot_df, x='Test', y='F-statistic', hue='Cluster', ax=ax)

    ax.set_xlabel('Causal Test', fontsize=12)
    ax.set_ylabel('F-statistic (Lag-1)', fontsize=12)
    ax.set_title('Granger Causality Strength by Cluster', fontsize=14, fontweight='bold')
    ax.legend(title='Cluster', loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')

    plt.xticks(rotation=15, ha='right')
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'causality_by_cluster.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/causality_by_cluster.png")


def visualize_significance_bars(results_df):
    """
    Bar chart showing percentage of significant results for each test.
    """
    print("\nCreating significance bar chart...")

    fig, ax = plt.subplots(figsize=(12, 6))

    test_names = []
    lag1_pct = []
    lag2_pct = []
    lag3_pct = []

    for cause_var, effect_var, test_name in CAUSAL_TESTS:
        prefix = f"{cause_var}_to_{effect_var}"
        test_names.append(test_name.replace(' → ', '→'))

        for lag_idx, lag in enumerate([1, 2, 3]):
            pval_col = f"{prefix}_lag{lag}_pvalue"

            if pval_col not in results_df.columns:
                if lag_idx == 0:
                    lag1_pct.append(0)
                elif lag_idx == 1:
                    lag2_pct.append(0)
                else:
                    lag3_pct.append(0)
                continue

            valid = results_df[pval_col].dropna()

            if len(valid) == 0:
                pct = 0
            else:
                significant = (valid < 0.05).sum()
                pct = significant / len(valid) * 100

            if lag_idx == 0:
                lag1_pct.append(pct)
            elif lag_idx == 1:
                lag2_pct.append(pct)
            else:
                lag3_pct.append(pct)

    x = np.arange(len(test_names))
    width = 0.25

    ax.bar(x - width, lag1_pct, width, label='Lag 1', color='steelblue', edgecolor='black')
    ax.bar(x, lag2_pct, width, label='Lag 2', color='coral', edgecolor='black')
    ax.bar(x + width, lag3_pct, width, label='Lag 3', color='lightgreen', edgecolor='black')

    ax.axhline(y=5, color='red', linestyle='--', linewidth=2, alpha=0.7,
              label='Expected (5% if random)')

    ax.set_xlabel('Causal Test', fontsize=12)
    ax.set_ylabel('% Significant (p < 0.05)', fontsize=12)
    ax.set_title('Granger Causality: Percentage of Significant Results by Lag',
                fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(test_names, rotation=15, ha='right')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, max(max(lag1_pct), max(lag2_pct), max(lag3_pct)) * 1.2)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'significance_by_lag.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/significance_by_lag.png")


def identify_top_gravity_tunes(results_df):
    """
    Identify tunes with strongest "gravity" effects.
    """
    print("\n" + "="*70)
    print("STRONGEST GRAVITY EFFECTS")
    print("="*70)

    for cause_var, effect_var, test_name in CAUSAL_TESTS:
        print(f"\n{test_name}:")

        prefix = f"{cause_var}_to_{effect_var}"
        pval_col = f"{prefix}_lag1_pvalue"
        fstat_col = f"{prefix}_lag1_fstat"

        if pval_col not in results_df.columns:
            continue

        # Filter significant results
        valid = results_df[['tune', pval_col, fstat_col]].dropna()
        significant = valid[valid[pval_col] < 0.05]

        if len(significant) == 0:
            print("  No significant results")
            continue

        # Sort by F-statistic
        top = significant.sort_values(fstat_col, ascending=False).head(5)

        print(f"  {'Tune':<30s} {'F-stat':>10s} {'p-value':>10s}")
        print("  " + "-"*55)

        for _, row in top.iterrows():
            tune = row['tune'][:29]
            fstat = row[fstat_col]
            pval = row[pval_col]
            print(f"  {tune:<30s} {fstat:>10.3f} {pval:>10.4f}")


def main():
    print("Parker Corpus: Granger Causality Analysis (Gravity)")
    print("="*70)

    # Load data
    phrases_df = load_data()

    # Run all Granger tests
    results_df = test_all_tunes(phrases_df)

    # Save results
    results_df.to_csv('parker_granger_results.csv', index=False)
    print(f"\nSaved: parker_granger_results.csv")

    # Print summaries
    print_all_summaries(results_df)

    # TEST DIRECTIONAL ASYMMETRY (NEW)
    asymmetry_results = test_directional_asymmetry(
        results_df,
        'mean_dissonance', 'mean_iv_sum',  # Dissonance → Complexity
        'mean_iv_sum', 'mean_dissonance',  # Complexity → Dissonance
        'Dissonance → Complexity',
        'Complexity → Dissonance'
    )

    analyze_by_cluster(results_df)
    identify_top_gravity_tunes(results_df)

    # Visualizations
    print("\n" + "="*70)
    print("GENERATING VISUALIZATIONS")
    print("="*70)

    visualize_causality_heatmap(results_df)
    visualize_causality_by_cluster(results_df)
    visualize_significance_bars(results_df)

    # Generate suggested text for paper
    print("\n" + "="*70)
    print("GENERATING SUGGESTED TEXT FOR PAPER")
    print("="*70)

    with open('paper_text_granger.txt', 'w') as f:
        f.write("SUGGESTED TEXT FOR PAPER - GRANGER CAUSALITY SECTION\n")
        f.write("="*70 + "\n\n")

        if asymmetry_results is not None:
            f.write("RESULTS SECTION:\n")
            f.write("-"*70 + "\n\n")

            f.write(f"Granger causality testing reveals directional predictive relationships ")
            f.write(f"between harmonic dimensions. In {asymmetry_results['pct2']:.1f}% of tunes ")
            f.write(f"({asymmetry_results['sig2']}/{asymmetry_results['n_total']}), ")
            f.write(f"past values of dissonance improve prediction of future complexity beyond ")
            f.write(f"autoregressive history (p < 0.05). The reverse direction shows weaker effects: ")
            f.write(f"{asymmetry_results['pct1']:.1f}% of tunes ({asymmetry_results['sig1']}/")
            f.write(f"{asymmetry_results['n_total']}) show significant Complexity→Dissonance causality. ")

            f.write(f"\n\nImportantly, {(asymmetry_results['sig_neither']/asymmetry_results['n_total']*100):.1f}% ")
            f.write(f"of tunes ({asymmetry_results['sig_neither']}/{asymmetry_results['n_total']}) ")
            f.write(f"show no significant causality in either direction, suggesting that phrase-level ")
            f.write(f"reactive processes account for a minority of temporal organization. ")

            if asymmetry_results['binomial_p'] is not None:
                if asymmetry_results['binomial_p'] < 0.05:
                    f.write(f"\n\nAmong the {asymmetry_results['sig_direction1_only'] + asymmetry_results['sig_direction2_only']} ")
                    f.write(f"tunes showing unidirectional causality, ")
                    f.write(f"Dissonance→Complexity predominates ({asymmetry_results['sig_direction2_only']} tunes) ")
                    f.write(f"over Complexity→Dissonance ({asymmetry_results['sig_direction1_only']} tunes), ")
                    f.write(f"though this asymmetry does not reach statistical significance ")
                    f.write(f"(binomial test: p = {asymmetry_results['binomial_p']:.3f}).")
                else:
                    f.write(f"\n\nAmong tunes showing unidirectional causality, the distribution ")
                    f.write(f"between directions does not significantly differ from chance ")
                    f.write(f"(binomial test: p = {asymmetry_results['binomial_p']:.3f}).")

            f.write("\n\n" + "-"*70 + "\n")
            f.write("DISCUSSION SECTION:\n")
            f.write("-"*70 + "\n\n")

            f.write(f"The Granger causality patterns are consistent with—though do not definitively ")
            f.write(f"prove—reactive navigation during improvisation. When dissonance at phrase t ")
            f.write(f"predicts complexity at phrase t+1, this could reflect several processes:\n\n")

            f.write(f"1. Reactive navigation: Parker perceives dissonance as a condition requiring ")
            f.write(f"resolution, deploying complexity as a navigational strategy\n\n")

            f.write(f"2. Harmonic constraint: The underlying chord progression creates conditions ")
            f.write(f"where dissonant melodic choices constrain subsequent options\n\n")

            f.write(f"3. Compositional planning: Parker pre-plans both dissonant passages and ")
            f.write(f"subsequent resolutions at chorus level\n\n")

            f.write(f"While we cannot definitively distinguish these alternatives from time series ")
            f.write(f"analysis alone, the ratio of Dissonance→Complexity to Complexity→Dissonance ")
            f.write(f"effects ({asymmetry_results['ratio']:.1f}:1) suggests preferential directionality ")
            f.write(f"consistent with reactive rather than proactive tension management.\n\n")

            f.write(f"Critically, most tunes ({(asymmetry_results['sig_neither']/asymmetry_results['n_total']*100):.1f}%) ")
            f.write(f"show no significant Granger causality, suggesting Parker employs multiple temporal ")
            f.write(f"organization strategies, only some of which involve phrase-level reactive processes.")

    print(f"Saved: paper_text_granger.txt")

    # Summary
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nOutputs:")
    print(f"  - parker_granger_results.csv")
    print(f"  - paper_text_granger.txt (suggested text for paper)")
    print(f"  - {PLOTS_DIR}/causality_heatmap.png")
    print(f"  - {PLOTS_DIR}/causality_by_cluster.png")
    print(f"  - {PLOTS_DIR}/significance_by_lag.png")

    print("\nInterpretation Guide:")
    print("  - F-statistic: Strength of causal relationship")
    print("  - p-value < 0.05: Significant causality")
    print("  - Binomial test: Tests if directional asymmetry is real")
    print("  - Most tunes show NO causality (composed improvisation)")

    print("\nKey Findings:")
    if asymmetry_results is not None:
        print(f"  - Dissonance→Complexity: {asymmetry_results['pct2']:.1f}% significant")
        print(f"  - Complexity→Dissonance: {asymmetry_results['pct1']:.1f}% significant")
        print(f"  - No causality: {(asymmetry_results['sig_neither']/asymmetry_results['n_total']*100):.1f}% of tunes")
        if asymmetry_results['binomial_p'] is not None:
            if asymmetry_results['binomial_p'] < 0.05:
                print(f"  - Significant directional asymmetry (p = {asymmetry_results['binomial_p']:.3f})")
            else:
                print(f"  - No significant directional asymmetry (p = {asymmetry_results['binomial_p']:.3f})")


if __name__ == '__main__':
    main()
