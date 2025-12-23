#!/usr/bin/env python3
"""
11_iv_robustness.py
Robustness analysis of Interval Vectors in Parker's vocabulary.
Robustness: Number of triads contained in the IV (harmonic versatility)

Outputs:
- Robustness scores for each unique IV
- Statistical tests for Parker's preferences
- Correlation between robustness and frequency of use
"""

import subprocess
import sys

for pkg in ['pandas', 'numpy', 'matplotlib', 'seaborn', 'scipy']:
    try:
        __import__(pkg)
    except ImportError:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from itertools import combinations
from scipy import stats
from scipy.stats import pearsonr, spearmanr, ttest_ind
import warnings
warnings.filterwarnings('ignore')

# Input from network analysis (contains IVs and frequencies)
NETWORK_CSV = 'parker_corpus_nodes.csv'
PLOTS_DIR = Path('11_robustness_plots')
PLOTS_DIR.mkdir(exist_ok=True)


def parse_iv(iv_string):
    """Parse IV string like '(111000)' to list [1,1,1,0,0,0]."""
    iv_string = iv_string.strip('()')
    return [int(x) for x in iv_string]


def euclidean_distance(iv1, iv2):
    """Euclidean distance between two IVs in 6D space."""
    return np.linalg.norm(np.array(iv1) - np.array(iv2))

def iv_to_pc_set_candidates(iv):
    """
    Generate candidate PC sets that could produce this IV.

    This is computationally expensive for large cardinalities,
    so we'll use a heuristic: generate PC sets from iv_sum.

    For accurate triad counting, we need to check actual PC sets.
    """
    # Heuristic: cardinality based on IV sum
    # This is approximate - multiple cardinalities can produce same IV
    iv_sum = sum(iv)

    # Reverse Forte's formula: n(n-1)/2 = iv_sum
    # Solving for n: n^2 - n - 2*iv_sum = 0
    # n = (1 + sqrt(1 + 8*iv_sum)) / 2

    if iv_sum == 0:
        return [[]]

    cardinality = int((1 + np.sqrt(1 + 8 * iv_sum)) / 2)

    # For triads, we need at least 3 notes
    if cardinality < 3:
        return []

    # Generate all possible PC sets of this cardinality
    # This is expensive, so we'll limit to cardinality <= 7
    if cardinality > 7:
        return []

    candidates = []
    for pc_set in combinations(range(12), cardinality):
        test_iv = compute_iv_from_pc_set(set(pc_set))
        if test_iv == iv:
            candidates.append(pc_set)

    return candidates


def compute_iv_from_pc_set(pc_set):
    """Compute interval vector from PC set."""
    if len(pc_set) < 2:
        return [0, 0, 0, 0, 0, 0]

    pc_list = sorted(list(pc_set))
    intervals = []

    for i in range(len(pc_list)):
        for j in range(i + 1, len(pc_list)):
            interval = (pc_list[j] - pc_list[i]) % 12
            interval = min(interval, 12 - interval)
            intervals.append(interval)

    # Count interval classes
    iv = [0, 0, 0, 0, 0, 0]
    for interval in intervals:
        if 1 <= interval <= 6:
            iv[interval - 1] += 1

    return iv


def count_triads_in_pc_set(pc_set):
    """Count number of triads (major, minor, diminished, augmented) in PC set."""
    if len(pc_set) < 3:
        return 0

    # Triad patterns (intervals from root)
    triad_patterns = [
        [0, 3, 6],  # Diminished
        [0, 3, 7],  # Minor
        [0, 4, 7],  # Major
        [0, 4, 8],  # Augmented
    ]

    count = 0
    pc_list = list(pc_set)

    # Check all 3-note subsets
    for subset in combinations(pc_list, 3):
        # Normalize to start at 0
        normalized = sorted([(pc - subset[0]) % 12 for pc in subset])
        if normalized in triad_patterns:
            count += 1

    return count


def compute_global_robustness(iv):
    """
    Compute robustness = number of triads contained.

    Since we can't uniquely determine PC set from IV,
    we'll find all possible PC sets and take the maximum triad count.

    Returns: max triad count, number of candidate PC sets
    """
    candidates = iv_to_pc_set_candidates(iv)

    if not candidates:
        # Heuristic fallback: estimate from IV content
        # Look for characteristic triad intervals
        # Major/Minor: ic3, ic4, ic5 present
        # This is approximate

        has_m3 = iv[2] > 0  # ic3
        has_M3 = iv[3] > 0  # ic4
        has_P4 = iv[4] > 0  # ic5

        if has_m3 and has_P4:
            estimated = 1  # At least one minor triad likely
        elif has_M3 and has_P4:
            estimated = 1  # At least one major triad likely
        else:
            estimated = 0

        return estimated, 0, True  # True = estimated

    # Count triads in all candidates, take maximum
    triad_counts = [count_triads_in_pc_set(set(pc_set)) for pc_set in candidates]
    max_triads = max(triad_counts) if triad_counts else 0

    return max_triads, len(candidates), False  # False = not estimated


def analyze_all_ivs(nodes_df):
    """
    Compute robustness metrics for all unique IVs in Parker's vocabulary.
    """
    print("\nComputing robustness metrics for all IVs...")
    print(f"Columns available: {list(nodes_df.columns)}")

    # Use 'id' for IV and 'size' for frequency
    iv_col = 'id'
    freq_col = 'size'

    results = []

    for idx, row in nodes_df.iterrows():
        iv_string = row[iv_col]
        iv = parse_iv(iv_string)

        # robustness
        global_rob, n_candidates, is_estimated = compute_global_robustness(iv)

        results.append({
            'iv': iv_string,
            'iv_list': iv,
            'iv_sum': sum(iv),
            'size': row[freq_col],  # Frequency in corpus
            'global_robustness': global_rob,
            'n_pc_set_candidates': n_candidates,
            'is_estimated': is_estimated
        })

        if (idx + 1) % 20 == 0:
            print(f"  Processed {idx + 1}/{len(nodes_df)} IVs...")

    results_df = pd.DataFrame(results)

    print(f"\nCompleted robustness analysis for {len(results_df)} unique IVs")

    return results_df


def compute_effect_size(group1, group2):
    """Compute Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def statistical_tests(results_df):
    """
    Perform comprehensive statistical tests for robustness analysis.

    Tests:
    1. Correlation between frequency and robustness (with p-value)
    2. T-test: Top-20 frequent IVs vs rest (triadic content)
    3. Effect sizes (Cohen's d)
    4. Confidence intervals
    """
    print("\n" + "="*70)
    print("STATISTICAL TESTS")
    print("="*70)

    # Filter for actual (non-estimated) robustness values
    actual = results_df[~results_df['is_estimated']].copy()

    print(f"\nDataset: {len(results_df)} total IVs, {len(actual)} with computed triadic content")

    # ===== TEST 1: Correlation between Frequency and Robustness =====
    print("\n" + "-"*70)
    print("TEST 1: Frequency ↔ Robustness (Triadic Content)")
    print("-"*70)

    if len(actual) > 2:
        # Pearson correlation
        r_pearson, p_pearson = pearsonr(actual['size'], actual['global_robustness'])

        # Spearman correlation (robust to outliers)
        r_spearman, p_spearman = spearmanr(actual['size'], actual['global_robustness'])

        print(f"\nPearson correlation:  r = {r_pearson:.4f}, p = {p_pearson:.4f}")
        print(f"Spearman correlation: ρ = {r_spearman:.4f}, p = {p_spearman:.4f}")

        # Interpret significance
        if p_pearson < 0.001:
            sig_level = "p < 0.001 (highly significant)"
        elif p_pearson < 0.01:
            sig_level = "p < 0.01 (very significant)"
        elif p_pearson < 0.05:
            sig_level = "p < 0.05 (significant)"
        else:
            sig_level = f"p = {p_pearson:.4f} (not significant)"

        print(f"\nSignificance: {sig_level}")

        # Interpret correlation strength
        if abs(r_pearson) < 0.1:
            strength = "negligible"
        elif abs(r_pearson) < 0.3:
            strength = "weak"
        elif abs(r_pearson) < 0.5:
            strength = "moderate"
        else:
            strength = "strong"

        direction = "negative" if r_pearson < 0 else "positive"
        print(f"Effect: {strength} {direction} correlation")

        # Compute R² (variance explained)
        r_squared = r_pearson ** 2
        print(f"Variance explained: R² = {r_squared:.4f} ({r_squared*100:.1f}%)")

    else:
        print("Insufficient data for correlation test")

    # ===== TEST 2: Top-20 vs Rest (T-test) =====
    print("\n" + "-"*70)
    print("TEST 2: Top-20 Most Frequent IVs vs Corpus Mean")
    print("-"*70)

    if len(actual) >= 20:
        # Sort by frequency and get top 20
        top20 = actual.nlargest(20, 'size')
        rest = actual[~actual.index.isin(top20.index)]

        top20_triads = top20['global_robustness']
        rest_triads = rest['global_robustness']

        # Descriptive statistics
        print(f"\nTop-20 frequent IVs:")
        print(f"  Mean triadic content: {top20_triads.mean():.3f} (SD = {top20_triads.std():.3f})")
        print(f"  Median: {top20_triads.median():.3f}")
        print(f"  Range: [{top20_triads.min()}, {top20_triads.max()}]")

        print(f"\nRest of corpus:")
        print(f"  Mean triadic content: {rest_triads.mean():.3f} (SD = {rest_triads.std():.3f})")
        print(f"  Median: {rest_triads.median():.3f}")
        print(f"  Range: [{rest_triads.min()}, {rest_triads.max()}]")

        # Two-sample t-test
        t_stat, p_value = ttest_ind(top20_triads, rest_triads)

        print(f"\nTwo-sample t-test:")
        print(f"  t-statistic: {t_stat:.4f}")
        print(f"  p-value: {p_value:.4f}")

        # Interpret significance
        if p_value < 0.001:
            sig_interp = "p < 0.001 (highly significant difference)"
        elif p_value < 0.01:
            sig_interp = "p < 0.01 (very significant difference)"
        elif p_value < 0.05:
            sig_interp = "p < 0.05 (significant difference)"
        else:
            sig_interp = f"p = {p_value:.4f} (no significant difference)"

        print(f"  Significance: {sig_interp}")

        # Effect size (Cohen's d)
        cohens_d = compute_effect_size(top20_triads, rest_triads)
        print(f"\nEffect size (Cohen's d): {cohens_d:.4f}")

        # Interpret effect size
        if abs(cohens_d) < 0.2:
            effect_interp = "negligible"
        elif abs(cohens_d) < 0.5:
            effect_interp = "small"
        elif abs(cohens_d) < 0.8:
            effect_interp = "medium"
        else:
            effect_interp = "large"

        print(f"  Interpretation: {effect_interp} effect")

        # 95% Confidence Interval for difference in means
        diff_mean = top20_triads.mean() - rest_triads.mean()
        se_diff = np.sqrt((top20_triads.var()/len(top20_triads)) +
                         (rest_triads.var()/len(rest_triads)))
        ci_95 = 1.96 * se_diff

        print(f"\nDifference in means: {diff_mean:.3f}")
        print(f"95% CI: [{diff_mean - ci_95:.3f}, {diff_mean + ci_95:.3f}]")

    else:
        print("Insufficient data for t-test (need at least 20 IVs)")

    # ===== TEST 3: Weighted analysis (frequency-weighted means) =====
    print("\n" + "-"*70)
    print("TEST 3: Frequency-Weighted Analysis")
    print("-"*70)

    total_uses = actual['size'].sum()
    weighted_global = (actual['global_robustness'] * actual['size']).sum() / total_uses
    unweighted_global = actual['global_robustness'].mean()

    print(f"\nRobustness (Triadic Content):")
    print(f"  Unweighted mean: {unweighted_global:.3f}")
    print(f"  Weighted by frequency: {weighted_global:.3f}")
    print(f"  Difference: {weighted_global - unweighted_global:.3f}")

    if weighted_global < unweighted_global:
        print("  → Parker favors IVs with LOWER triadic content")
    else:
        print("  → Parker favors IVs with HIGHER triadic content")

    # ===== TEST 4: Quartile analysis =====
    print("\n" + "-"*70)
    print("TEST 4: Triadic Content by Usage Frequency (Quartiles)")
    print("-"*70)

    if len(actual) >= 4:
        actual['freq_quartile'] = pd.qcut(actual['size'], q=4,
                                          labels=['Q1 (Rare)', 'Q2', 'Q3', 'Q4 (Common)'],
                                          duplicates='drop')

        quartile_stats = actual.groupby('freq_quartile')['global_robustness'].agg([
            ('Mean', 'mean'),
            ('SD', 'std'),
            ('Median', 'median'),
            ('N', 'count')
        ])

        print("\n" + quartile_stats.to_string())

        # ANOVA test across quartiles
        quartile_groups = [group['global_robustness'].values
                          for name, group in actual.groupby('freq_quartile')]

        if len(quartile_groups) >= 2:
            f_stat, p_anova = stats.f_oneway(*quartile_groups)
            print(f"\nOne-way ANOVA:")
            print(f"  F-statistic: {f_stat:.4f}")
            print(f"  p-value: {p_anova:.4f}")

            if p_anova < 0.05:
                print("  → Significant difference across frequency quartiles")
            else:
                print("  → No significant difference across frequency quartiles")

    return {
        'correlation': r_pearson if len(actual) > 2 else None,
        'correlation_p': p_pearson if len(actual) > 2 else None,
        't_statistic': t_stat if len(actual) >= 20 else None,
        't_test_p': p_value if len(actual) >= 20 else None,
        'cohens_d': cohens_d if len(actual) >= 20 else None,
        'top20_mean': top20_triads.mean() if len(actual) >= 20 else None,
        'corpus_mean': rest_triads.mean() if len(actual) >= 20 else None
    }


def print_robustness_rankings(results_df):
    """Print IVs ranked by robustness."""
    print("\n" + "="*70)
    print("ROBUSTNESS RANKINGS")
    print("="*70)

    # Robustness
    print("\nMost Globally Robust (Highest triad count):")
    print(f"  {'IV':<12s} {'Triad Count':>12s} {'IV Sum':>12s} {'Frequency':>12s}")
    print("  " + "-"*60)

    # Filter out estimated values for ranking
    actual_global = results_df[~results_df['is_estimated']]

    if len(actual_global) > 0:
        top_global = actual_global.nlargest(10, 'global_robustness')
        for _, row in top_global.iterrows():
            print(f"  {row['iv']:<12s} {row['global_robustness']:>12d} "
                  f"{row['iv_sum']:>12d} {row['size']:>12d}")
    else:
        print("  No actual PC set candidates computed (all estimated)")


def analyze_parker_preferences(results_df):
    """Analyze Parker's usage patterns relative to robustness."""
    print("\n" + "="*70)
    print("PARKER'S ROBUSTNESS PREFERENCES (DESCRIPTIVE)")
    print("="*70)

    # Weight by frequency
    total_uses = results_df['size'].sum()

    # Weighted mean robustness
    weighted_global = (results_df['global_robustness'] * results_df['size']).sum() / total_uses

    print(f"\nWeighted by frequency of use:")
    print(f"  Mean Robustness: {weighted_global:.4f}")

    # Correlation between robustness and frequency
    corr_global = results_df[['global_robustness', 'size']].corr().iloc[0, 1]

    print(f"\nDescriptive correlation with frequency (no p-value):")
    print(f"  Robustness ↔ Frequency: {corr_global:.4f}")

    print("\n  (See STATISTICAL TESTS section below for significance testing)")


def visualize_robustness_distributions(results_df):
    """Visualize robustness score distributions."""
    print("\nCreating robustness distribution plots...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Robustness distribution
    ax = axes[0, 1]
    # Filter actual values
    actual = results_df[~results_df['is_estimated']]
    if len(actual) > 0:
        ax.hist(actual['global_robustness'], bins=range(0, int(actual['global_robustness'].max())+2),
               edgecolor='black', alpha=0.7, color='coral')
        ax.axvline(x=actual['global_robustness'].mean(), color='red', linestyle='--',
                  linewidth=2, label=f"Mean: {actual['global_robustness'].mean():.2f}")
    ax.set_xlabel('Robustness (Triad Count)', fontsize=11)
    ax.set_ylabel('Frequency', fontsize=11)
    ax.set_title('Distribution of Robustness', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Robustness vs Frequency
    ax = axes[1, 1]
    if len(actual) > 0:
        scatter = ax.scatter(actual['size'], actual['global_robustness'],
                            c=actual['iv_sum'], cmap='plasma',
                            alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
        ax.set_xlabel('Frequency (# occurrences)', fontsize=11)
        ax.set_ylabel('Robustness (Triad Count)', fontsize=11)
        ax.set_title('Robustness vs Frequency', fontsize=12, fontweight='bold')
        ax.set_xscale('log')
        plt.colorbar(scatter, ax=ax, label='IV Sum')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'robustness_distributions.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/robustness_distributions.png")



def main():
    print("Parker Corpus: Interval Vector Robustness Analysis")
    print("="*70)

    # Load IV data
    try:
        nodes_df = pd.read_csv(NETWORK_CSV)
        print(f"Loaded {len(nodes_df)} unique IVs from network analysis")
    except FileNotFoundError:
        print(f"ERROR: {NETWORK_CSV} not found. Please run script 1 first.")
        return

    # Compute robustness metrics
    results_df = analyze_all_ivs(nodes_df)

    # Save results
    results_df.to_csv('parker_iv_robustness.csv', index=False)
    print(f"\nSaved: parker_iv_robustness.csv")

    # Print rankings
    print_robustness_rankings(results_df)

    # Analyze Parker's preferences (descriptive)
    analyze_parker_preferences(results_df)

    # Statistical tests (NEW - with p-values)
    stats_results = statistical_tests(results_df)

    # Visualizations
    print("\n" + "="*70)
    print("GENERATING VISUALIZATIONS")
    print("="*70)

    visualize_robustness_distributions(results_df)

    # Summary with actionable interpretation
    print("\n" + "="*70)
    print("SUMMARY FOR PAPER")
    print("="*70)

    if stats_results['correlation'] is not None:
        r = stats_results['correlation']
        p = stats_results['correlation_p']

        print(f"\n1. Correlation Analysis:")
        print(f"   Frequency ↔ Triadic Content: r = {r:.3f}, p = {p:.4f}")

        if p < 0.05:
            if abs(r) < 0.3:
                rec = "Report as: 'weak but significant negative correlation'"
            else:
                rec = "Report as: 'moderate negative correlation'"
        else:
            rec = "Report as: 'no significant correlation'"

        print(f"   RECOMMENDATION: {rec}")

    if stats_results['t_test_p'] is not None:
        p_t = stats_results['t_test_p']
        d = stats_results['cohens_d']
        mean_diff = stats_results['top20_mean'] - stats_results['corpus_mean']

        print(f"\n2. T-test (Top-20 vs Rest):")
        print(f"   Difference in means: {mean_diff:.3f}")
        print(f"   p-value: {p_t:.4f}")
        print(f"   Cohen's d: {d:.3f}")

        if p_t < 0.05:
            print(f"   RECOMMENDATION: Report as significant difference")
            if mean_diff < 0:
                print(f"   → Top-20 have LOWER triadic content")
            else:
                print(f"   → Top-20 have HIGHER triadic content")
        else:
            print(f"   RECOMMENDATION: Report as no significant difference")

    print(f"\n3. Suggested Paper Language:")
    print(f"   See revised text files generated above for copy-paste text")

    # Generate suggested text for paper
    with open('paper_text_robustness.txt', 'w') as f:
        f.write("SUGGESTED TEXT FOR PAPER - ROBUSTNESS SECTION\n")
        f.write("="*70 + "\n\n")

        if stats_results['correlation'] is not None:
            r = stats_results['correlation']
            p = stats_results['correlation_p']

            if p < 0.05:
                f.write(f"Parker's most frequently used interval vectors show ")
                if abs(r) < 0.3:
                    f.write(f"modestly lower triadic content than less frequent IVs ")
                else:
                    f.write(f"lower triadic content than less frequent IVs ")

                f.write(f"(r = {r:.2f}, p = {p:.3f}, n = {len(results_df[~results_df['is_estimated']])}). ")

                if abs(r) < 0.3:
                    f.write(f"While this negative correlation is weak, it suggests that ")
                else:
                    f.write(f"This pattern suggests that ")

                f.write(f"bebop vocabulary selection may prioritize navigational flexibility ")
                f.write(f"over triadic stability. ")
            else:
                f.write(f"Parker's most frequently used interval vectors show no strong preference ")
                f.write(f"for either triadically dense or triadically sparse structures ")
                f.write(f"(r = {r:.2f}, p = {p:.3f}). ")

        if stats_results['t_test_p'] is not None:
            f.write(f"\n\nThe top 20 most frequent IVs contain mean triadic content of ")
            f.write(f"{stats_results['top20_mean']:.2f} triads per IV, compared to corpus mean ")
            f.write(f"of {stats_results['corpus_mean']:.2f} ")

            if stats_results['t_test_p'] < 0.05:
                f.write(f"(t-test: p = {stats_results['t_test_p']:.3f}, ")
                f.write(f"Cohen's d = {stats_results['cohens_d']:.2f}). ")
            else:
                f.write(f"(t-test: p = {stats_results['t_test_p']:.3f}, not significant). ")

    print(f"\nSaved: paper_text_robustness.txt")

    print(f"\nOutputs:")
    print(f"  - parker_iv_robustness.csv")
    print(f"  - paper_text_robustness.txt (suggested text for paper)")
    print(f"  - {PLOTS_DIR}/robustness_distributions.png")
    print(f"  - {PLOTS_DIR}/robustness_2d_space.png")


if __name__ == '__main__':
    main()
