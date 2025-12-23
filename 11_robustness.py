#!/usr/bin/env python3
"""
11_iv_robustness.py
Local and Global Robustness analysis of Interval Vectors in Parker's vocabulary.

Local Robustness: Sensitivity to perturbation of IC values (vector arithmetic)
Global Robustness: Number of triads contained in the IV (harmonic versatility)

Outputs:
- Robustness scores for each unique IV
- Analysis of Parker's preference for robust vs fragile IVs
- Correlation between robustness and frequency of use
"""

import subprocess
import sys

for pkg in ['pandas', 'numpy', 'matplotlib', 'seaborn']:
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


def compute_local_robustness(iv):
    """
    Compute local robustness by perturbing each IC component.
    
    Method: For each IC position, try +1 and -1 perturbations.
    Measure average Euclidean distance to perturbed versions.
    
    Robustness = 1 / (average distance from perturbations)
    High robustness = small changes from perturbations (stable)
    Low robustness = large changes from perturbations (fragile)
    
    Returns: robustness score, mean perturbation distance, perturbation details
    """
    perturbations = []
    
    for ic_idx in range(6):
        # Perturbation +1
        perturbed_plus = iv.copy()
        perturbed_plus[ic_idx] += 1
        dist_plus = euclidean_distance(iv, perturbed_plus)
        perturbations.append({
            'ic_position': ic_idx + 1,
            'operation': '+1',
            'distance': dist_plus
        })
        
        # Perturbation -1 (only if current value > 0)
        if iv[ic_idx] > 0:
            perturbed_minus = iv.copy()
            perturbed_minus[ic_idx] -= 1
            dist_minus = euclidean_distance(iv, perturbed_minus)
            perturbations.append({
                'ic_position': ic_idx + 1,
                'operation': '-1',
                'distance': dist_minus
            })
    
    # Calculate mean perturbation distance
    distances = [p['distance'] for p in perturbations]
    mean_distance = np.mean(distances)
    
    # Robustness score: inverse of mean distance
    # Add small epsilon to avoid division by zero
    robustness = 1.0 / (mean_distance + 1e-6)
    
    return robustness, mean_distance, perturbations


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
    Compute global robustness = number of triads contained.
    
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

        # Local robustness
        local_rob, mean_dist, perturbations = compute_local_robustness(iv)

        # Global robustness
        global_rob, n_candidates, is_estimated = compute_global_robustness(iv)

        results.append({
            'iv': iv_string,
            'iv_list': iv,
            'iv_sum': sum(iv),
            'size': row[freq_col],  # Frequency in corpus
            'local_robustness': local_rob,
            'mean_perturbation_distance': mean_dist,
            'global_robustness': global_rob,
            'n_pc_set_candidates': n_candidates,
            'is_estimated': is_estimated
        })

        if (idx + 1) % 20 == 0:
            print(f"  Processed {idx + 1}/{len(nodes_df)} IVs...")

    results_df = pd.DataFrame(results)

    print(f"\nCompleted robustness analysis for {len(results_df)} unique IVs")

    return results_df


def print_robustness_rankings(results_df):
    """Print IVs ranked by robustness."""
    print("\n" + "="*70)
    print("ROBUSTNESS RANKINGS")
    print("="*70)

    # Local Robustness
    print("\nMost Locally Robust (Stable under perturbation):")
    print(f"  {'IV':<12s} {'Local Rob':>12s} {'Mean Dist':>12s} {'Frequency':>12s}")
    print("  " + "-"*60)

    top_local = results_df.nlargest(10, 'local_robustness')
    for _, row in top_local.iterrows():
        print(f"  {row['iv']:<12s} {row['local_robustness']:>12.4f} "
              f"{row['mean_perturbation_distance']:>12.4f} {row['size']:>12d}")

    print("\nMost Locally Fragile (Sensitive to perturbation):")
    print(f"  {'IV':<12s} {'Local Rob':>12s} {'Mean Dist':>12s} {'Frequency':>12s}")
    print("  " + "-"*60)

    bottom_local = results_df.nsmallest(10, 'local_robustness')
    for _, row in bottom_local.iterrows():
        print(f"  {row['iv']:<12s} {row['local_robustness']:>12.4f} "
              f"{row['mean_perturbation_distance']:>12.4f} {row['size']:>12d}")

    # Global Robustness
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
    print("PARKER'S ROBUSTNESS PREFERENCES")
    print("="*70)

    # Weight by frequency
    total_uses = results_df['size'].sum()

    # Weighted mean robustness
    weighted_local = (results_df['local_robustness'] * results_df['size']).sum() / total_uses
    weighted_global = (results_df['global_robustness'] * results_df['size']).sum() / total_uses

    print(f"\nWeighted by frequency of use:")
    print(f"  Mean Local Robustness: {weighted_local:.4f}")
    print(f"  Mean Global Robustness: {weighted_global:.4f}")

    # Correlation between robustness and frequency
    corr_local = results_df[['local_robustness', 'size']].corr().iloc[0, 1]
    corr_global = results_df[['global_robustness', 'size']].corr().iloc[0, 1]

    print(f"\nCorrelation with frequency of use:")
    print(f"  Local Robustness ↔ Frequency: {corr_local:.4f}")
    print(f"  Global Robustness ↔ Frequency: {corr_global:.4f}")

    if corr_local > 0.3:
        print("    → Parker favors locally STABLE IVs")
    elif corr_local < -0.3:
        print("    → Parker favors locally FRAGILE IVs")
    else:
        print("    → Parker shows no strong preference for local stability")

    if corr_global > 0.3:
        print("    → Parker favors IVs with HIGH triadic content")
    elif corr_global < -0.3:
        print("    → Parker favors IVs with LOW triadic content")
    else:
        print("    → Parker shows no strong preference for triadic content")

    # Quartile analysis
    print(f"\nRobustness by usage frequency (quartiles):")
    results_df['freq_quartile'] = pd.qcut(results_df['size'], q=4, labels=['Q1 (Rare)', 'Q2', 'Q3', 'Q4 (Common)'])

    quartile_stats = results_df.groupby('freq_quartile').agg({
        'local_robustness': 'mean',
        'global_robustness': 'mean',
        'size': 'sum'
    })

    print(quartile_stats.to_string())


def visualize_robustness_distributions(results_df):
    """Visualize robustness score distributions."""
    print("\nCreating robustness distribution plots...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Local Robustness distribution
    ax = axes[0, 0]
    ax.hist(results_df['local_robustness'], bins=30, edgecolor='black', alpha=0.7, color='steelblue')
    ax.axvline(x=results_df['local_robustness'].mean(), color='red', linestyle='--',
               linewidth=2, label=f"Mean: {results_df['local_robustness'].mean():.3f}")
    ax.set_xlabel('Local Robustness', fontsize=11)
    ax.set_ylabel('Frequency', fontsize=11)
    ax.set_title('Distribution of Local Robustness', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Global Robustness distribution
    ax = axes[0, 1]
    # Filter actual values
    actual = results_df[~results_df['is_estimated']]
    if len(actual) > 0:
        ax.hist(actual['global_robustness'], bins=range(0, actual['global_robustness'].max()+2),
               edgecolor='black', alpha=0.7, color='coral')
        ax.axvline(x=actual['global_robustness'].mean(), color='red', linestyle='--',
                  linewidth=2, label=f"Mean: {actual['global_robustness'].mean():.2f}")
    ax.set_xlabel('Global Robustness (Triad Count)', fontsize=11)
    ax.set_ylabel('Frequency', fontsize=11)
    ax.set_title('Distribution of Global Robustness', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Local Robustness vs Frequency
    ax = axes[1, 0]
    scatter = ax.scatter(results_df['size'], results_df['local_robustness'],
                        c=results_df['iv_sum'], cmap='viridis',
                        alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
    ax.set_xlabel('Frequency (# occurrences)', fontsize=11)
    ax.set_ylabel('Local Robustness', fontsize=11)
    ax.set_title('Local Robustness vs Frequency', fontsize=12, fontweight='bold')
    ax.set_xscale('log')
    plt.colorbar(scatter, ax=ax, label='IV Sum')
    ax.grid(True, alpha=0.3)

    # Global Robustness vs Frequency
    ax = axes[1, 1]
    if len(actual) > 0:
        scatter = ax.scatter(actual['size'], actual['global_robustness'],
                            c=actual['iv_sum'], cmap='plasma',
                            alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
        ax.set_xlabel('Frequency (# occurrences)', fontsize=11)
        ax.set_ylabel('Global Robustness (Triad Count)', fontsize=11)
        ax.set_title('Global Robustness vs Frequency', fontsize=12, fontweight='bold')
        ax.set_xscale('log')
        plt.colorbar(scatter, ax=ax, label='IV Sum')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'robustness_distributions.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/robustness_distributions.png")


def visualize_robustness_2d_space(results_df):
    """2D scatter: Local vs Global Robustness."""
    print("\nCreating 2D robustness space plot...")

    fig, ax = plt.subplots(figsize=(12, 8))

    # Filter actual global robustness values
    actual = results_df[~results_df['is_estimated']]

    if len(actual) > 0:
        scatter = ax.scatter(actual['local_robustness'], actual['global_robustness'],
                            s=actual['size']*2, c=actual['iv_sum'],
                            cmap='coolwarm', alpha=0.6,
                            edgecolors='black', linewidth=0.5)

        # Annotate most frequent IVs
        top_freq = actual.nlargest(5, 'size')
        for _, row in top_freq.iterrows():
            ax.annotate(row['iv'],
                       xy=(row['local_robustness'], row['global_robustness']),
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=9, alpha=0.8)

        ax.set_xlabel('Local Robustness (Stability)', fontsize=12)
        ax.set_ylabel('Global Robustness (Triad Count)', fontsize=12)
        ax.set_title("Parker's IV Space: Local vs Global Robustness",
                    fontsize=14, fontweight='bold')

        # Color bar
        cbar = plt.colorbar(scatter, ax=ax, label='IV Sum')

        # Legend for size
        sizes = [10, 50, 100, 200]
        labels = ['10', '50', '100', '200+']
        legend_elements = [plt.scatter([], [], s=s*2, c='gray', alpha=0.6,
                                      edgecolors='black', linewidth=0.5)
                          for s in sizes]
        legend = ax.legend(legend_elements, labels, title='Frequency',
                          loc='upper right', framealpha=0.9)

        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'robustness_2d_space.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/robustness_2d_space.png")


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

    # Analyze Parker's preferences
    analyze_parker_preferences(results_df)

    # Visualizations
    print("\n" + "="*70)
    print("GENERATING VISUALIZATIONS")
    print("="*70)

    visualize_robustness_distributions(results_df)
    visualize_robustness_2d_space(results_df)

    # Summary
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nOutputs:")
    print(f"  - parker_iv_robustness.csv")
    print(f"  - {PLOTS_DIR}/robustness_distributions.png")
    print(f"  - {PLOTS_DIR}/robustness_2d_space.png")

    print("\nKey Metrics:")
    print("  LOCAL ROBUSTNESS = 1 / (mean perturbation distance)")
    print("    High = stable under IC perturbation")
    print("    Low = fragile, sensitive to changes")
    print("\n  GLOBAL ROBUSTNESS = number of triads contained")
    print("    High = versatile, many Upper Structure options")
    print("    Low = limited triadic content")

    print("\nInterpretation:")
    print("  - Does Parker favor stable or fragile IVs?")
    print("  - Does he use IVs with high triadic content?")
    print("  - How do robustness and frequency correlate?")


if __name__ == '__main__':
    main()
