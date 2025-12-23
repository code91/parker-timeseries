#!/usr/bin/env python3
"""
6_vocabulary_expansion.py
Analyze how Parker's intervallic vocabulary expands across choruses.

Research Question: Does vocabulary expand across choruses?

Tracks:
- Cumulative unique IVs by chorus
- Cumulative unique transitions by chorus
- Marginal growth per chorus
- Saturation point analysis
- Per-tune growth patterns
- Late-appearing vocabulary characterization

Outputs to: expansion_plots/
"""

import subprocess
import sys

for pkg in ['pandas', 'numpy', 'matplotlib', 'scipy']:
    try:
        __import__(pkg)
    except ImportError:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from collections import defaultdict
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

INPUT_CSV = 'parker_timeseries.csv'
PLOTS_DIR = Path('06_expansion_plots')
PLOTS_DIR.mkdir(exist_ok=True)


def load_and_prepare_data(path: str) -> pd.DataFrame:
    """Load data and ensure chorus numbers are present."""
    df = pd.read_csv(path)
    df = df.dropna(subset=['timestamp_ms'])

    # Add chorus number if not present
    if 'chorus_num' not in df.columns:
        df['chorus_num'] = 1
        for tune in df['tune'].unique():
            mask = df['tune'] == tune
            max_measure = df.loc[mask, 'measure'].max()
            form_len = 12 if max_measure <= 24 else 32
            df.loc[mask, 'chorus_num'] = (df.loc[mask, 'measure'] // form_len).astype(int) + 1

    # Cap chorus number at 6 for analysis
    df['chorus_capped'] = df['chorus_num'].clip(upper=6)

    print(f"Loaded {len(df)} segments from {len(df['tune'].unique())} tunes")
    print(f"Chorus distribution:")
    for c in sorted(df['chorus_capped'].unique()):
        n = len(df[df['chorus_capped'] == c])
        label = f"{c}+" if c == 6 else str(c)
        print(f"  Chorus {label}: {n} segments")

    return df


def extract_transitions(df: pd.DataFrame) -> pd.DataFrame:
    """Extract all transitions with chorus information."""
    transitions = []
    df_sorted = df.sort_values(['tune', 'timestamp_ms'])

    for tune in df['tune'].unique():
        tune_df = df_sorted[df_sorted['tune'] == tune].reset_index(drop=True)

        for i in range(len(tune_df) - 1):
            transitions.append({
                'tune': tune,
                'source_iv': tune_df.loc[i, 'iv'],
                'target_iv': tune_df.loc[i+1, 'iv'],
                'chorus': tune_df.loc[i, 'chorus_capped'],
                'timestamp_ms': tune_df.loc[i, 'timestamp_ms']
            })

    return pd.DataFrame(transitions)


def compute_corpus_growth(df: pd.DataFrame, trans_df: pd.DataFrame) -> dict:
    """Compute cumulative vocabulary growth across entire corpus."""
    print("\n" + "="*70)
    print("CORPUS-LEVEL VOCABULARY EXPANSION")
    print("="*70)

    max_chorus = int(df['chorus_capped'].max())

    # Track cumulative sets
    seen_ivs = set()
    seen_edges = set()

    growth = {
        'chorus': [],
        'cumulative_ivs': [],
        'cumulative_edges': [],
        'new_ivs': [],
        'new_edges': [],
        'segments_seen': []
    }

    cumulative_segments = 0

    for chorus in range(1, max_chorus + 1):
        # IVs in this chorus
        chorus_ivs = set(df[df['chorus_capped'] == chorus]['iv'].unique())

        # Edges in this chorus
        chorus_edges = set(
            zip(trans_df[trans_df['chorus'] == chorus]['source_iv'],
                trans_df[trans_df['chorus'] == chorus]['target_iv'])
        )

        # New vocabulary
        new_ivs = chorus_ivs - seen_ivs
        new_edges = chorus_edges - seen_edges

        # Update seen sets
        seen_ivs.update(chorus_ivs)
        seen_edges.update(chorus_edges)

        cumulative_segments += len(df[df['chorus_capped'] == chorus])

        # Record
        growth['chorus'].append(chorus)
        growth['cumulative_ivs'].append(len(seen_ivs))
        growth['cumulative_edges'].append(len(seen_edges))
        growth['new_ivs'].append(len(new_ivs))
        growth['new_edges'].append(len(new_edges))
        growth['segments_seen'].append(cumulative_segments)

    # Compute percentages
    total_ivs = len(df['iv'].unique())
    total_edges = len(set(zip(trans_df['source_iv'], trans_df['target_iv'])))

    growth['iv_coverage'] = [c / total_ivs * 100 for c in growth['cumulative_ivs']]
    growth['edge_coverage'] = [c / total_edges * 100 for c in growth['cumulative_edges']]

    # Print results
    print("\n  CUMULATIVE GROWTH:")
    print("  " + "-"*65)
    print(f"  {'Chorus':<10} {'IVs':>8} {'Coverage':>10} {'Edges':>8} {'Coverage':>10}")
    print("  " + "-"*65)

    for i, chorus in enumerate(growth['chorus']):
        label = f"{chorus}+" if chorus == 6 else str(chorus)
        print(f"  {label:<10} {growth['cumulative_ivs'][i]:>8} "
              f"{growth['iv_coverage'][i]:>9.1f}% "
              f"{growth['cumulative_edges'][i]:>8} "
              f"{growth['edge_coverage'][i]:>9.1f}%")

    print("\n  MARGINAL GROWTH (new per chorus):")
    print("  " + "-"*50)
    print(f"  {'Chorus':<10} {'New IVs':>10} {'New Edges':>12}")
    print("  " + "-"*50)

    for i, chorus in enumerate(growth['chorus']):
        label = f"{chorus}+" if chorus == 6 else str(chorus)
        iv_bar = '█' * (growth['new_ivs'][i] // 2)
        print(f"  {label:<10} {growth['new_ivs'][i]:>10} {growth['new_edges'][i]:>12}  {iv_bar}")

    return growth


def compute_per_tune_growth(df: pd.DataFrame) -> pd.DataFrame:
    """Compute growth patterns for each tune."""
    print("\n" + "="*70)
    print("PER-TUNE VOCABULARY EXPANSION")
    print("="*70)

    tune_growth = []

    for tune in df['tune'].unique():
        tune_df = df[df['tune'] == tune].sort_values('timestamp_ms')
        max_chorus = int(tune_df['chorus_capped'].max())

        if max_chorus < 2:
            continue

        seen_ivs = set()

        chorus_1_ivs = set(tune_df[tune_df['chorus_capped'] == 1]['iv'].unique())
        final_ivs = set(tune_df['iv'].unique())

        seen_ivs.update(chorus_1_ivs)

        # Track chorus-by-chorus
        for chorus in range(2, max_chorus + 1):
            chorus_ivs = set(tune_df[tune_df['chorus_capped'] == chorus]['iv'].unique())
            seen_ivs.update(chorus_ivs)

        # Compute metrics
        chorus_1_coverage = len(chorus_1_ivs) / len(final_ivs) * 100 if final_ivs else 0

        tune_growth.append({
            'tune': tune,
            'max_chorus': max_chorus,
            'total_ivs': len(final_ivs),
            'chorus_1_ivs': len(chorus_1_ivs),
            'chorus_1_coverage': chorus_1_coverage,
            'late_ivs': len(final_ivs - chorus_1_ivs)
        })

    tune_df = pd.DataFrame(tune_growth)
    tune_df = tune_df.sort_values('chorus_1_coverage')

    print(f"\n  Analyzed {len(tune_df)} tunes with 2+ choruses")

    print("\n  MOST EXPLORATORY (lowest chorus 1 coverage):")
    print("  " + "-"*60)
    for _, row in tune_df.head(10).iterrows():
        bar = '█' * int(row['chorus_1_coverage'] / 5)
        print(f"    {row['tune'][:25]:<25} {row['chorus_1_coverage']:>5.1f}% {bar}")

    print("\n  MOST FRONT-LOADED (highest chorus 1 coverage):")
    print("  " + "-"*60)
    for _, row in tune_df.tail(10).iterrows():
        bar = '█' * int(row['chorus_1_coverage'] / 5)
        print(f"    {row['tune'][:25]:<25} {row['chorus_1_coverage']:>5.1f}% {bar}")

    print(f"\n  SUMMARY:")
    print(f"    Mean chorus 1 coverage: {tune_df['chorus_1_coverage'].mean():.1f}%")
    print(f"    Median chorus 1 coverage: {tune_df['chorus_1_coverage'].median():.1f}%")
    print(f"    Std dev: {tune_df['chorus_1_coverage'].std():.1f}%")

    return tune_df


def analyze_late_vocabulary(df: pd.DataFrame, trans_df: pd.DataFrame) -> pd.DataFrame:
    """Characterize vocabulary that appears late (after chorus 1)."""
    print("\n" + "="*70)
    print("LATE-APPEARING VOCABULARY ANALYSIS")
    print("="*70)

    # IVs in chorus 1
    chorus_1_ivs = set(df[df['chorus_capped'] == 1]['iv'].unique())

    # IVs that appear later
    all_ivs = set(df['iv'].unique())
    late_ivs = all_ivs - chorus_1_ivs

    # Also track late edges
    chorus_1_edges = set(
        zip(trans_df[trans_df['chorus'] == 1]['source_iv'],
            trans_df[trans_df['chorus'] == 1]['target_iv'])
    )
    all_edges = set(zip(trans_df['source_iv'], trans_df['target_iv']))
    late_edges = all_edges - chorus_1_edges

    print(f"\n  Chorus 1 vocabulary:")
    print(f"    IVs: {len(chorus_1_ivs)} ({len(chorus_1_ivs)/len(all_ivs)*100:.1f}%)")
    print(f"    Edges: {len(chorus_1_edges)} ({len(chorus_1_edges)/len(all_edges)*100:.1f}%)")

    print(f"\n  Late-appearing (chorus 2+):")
    print(f"    IVs: {len(late_ivs)} ({len(late_ivs)/len(all_ivs)*100:.1f}%)")
    print(f"    Edges: {len(late_edges)} ({len(late_edges)/len(all_edges)*100:.1f}%)")

    # Characterize late IVs
    if late_ivs:
        late_iv_data = []

        for iv in late_ivs:
            iv_df = df[df['iv'] == iv]
            first_chorus = iv_df['chorus_capped'].min()
            total_count = len(iv_df)
            iv_sum = sum(int(d) for d in iv.strip('()'))

            late_iv_data.append({
                'iv': iv,
                'first_chorus': first_chorus,
                'total_count': total_count,
                'iv_sum': iv_sum,
                'tunes': iv_df['tune'].nunique()
            })

        late_df = pd.DataFrame(late_iv_data)
        late_df = late_df.sort_values('total_count', ascending=False)

        print("\n  TOP LATE-APPEARING IVs (by frequency):")
        print("  " + "-"*60)
        print(f"  {'IV':<15} {'First':>7} {'Count':>7} {'Tunes':>7} {'IVSum':>7}")
        print("  " + "-"*60)

        for _, row in late_df.head(15).iterrows():
            print(f"  {row['iv']:<15} {row['first_chorus']:>7} "
                  f"{row['total_count']:>7} {row['tunes']:>7} {row['iv_sum']:>7}")

        # Compare complexity of early vs late
        early_iv_sums = [sum(int(d) for d in iv.strip('()')) for iv in chorus_1_ivs]
        late_iv_sums = [sum(int(d) for d in iv.strip('()')) for iv in late_ivs]

        print(f"\n  COMPLEXITY COMPARISON:")
        print(f"    Chorus 1 IVs mean complexity: {np.mean(early_iv_sums):.2f}")
        print(f"    Late IVs mean complexity: {np.mean(late_iv_sums):.2f}")

        if np.mean(late_iv_sums) > np.mean(early_iv_sums):
            print("    → Late vocabulary is MORE complex (warm-up pattern)")
        else:
            print("    → Late vocabulary is LESS complex (core first, periphery later)")

        return late_df

    return pd.DataFrame()


def analyze_saturation(growth: dict):
    """Fit saturation curve and identify saturation point."""
    print("\n" + "="*70)
    print("SATURATION ANALYSIS")
    print("="*70)

    x = np.array(growth['chorus'])
    y_ivs = np.array(growth['iv_coverage'])
    y_edges = np.array(growth['edge_coverage'])

    # Fit logarithmic curve: y = a * log(x) + b
    def log_func(x, a, b):
        return a * np.log(x) + b

    # Fit saturation curve: y = a * (1 - exp(-b*x))
    def sat_func(x, a, b):
        return a * (1 - np.exp(-b * x))

    try:
        # Fit IV curve
        popt_iv, _ = curve_fit(log_func, x, y_ivs, p0=[20, 50], maxfev=5000)
        iv_fit = log_func(x, *popt_iv)

        # Project to find 90% and 95% points
        x_extended = np.arange(1, 20)
        iv_projected = log_func(x_extended, *popt_iv)

        chorus_90 = x_extended[np.argmax(iv_projected >= 90)] if any(iv_projected >= 90) else ">19"
        chorus_95 = x_extended[np.argmax(iv_projected >= 95)] if any(iv_projected >= 95) else ">19"

        print(f"\n  IV SATURATION (logarithmic fit):")
        print(f"    Model: coverage = {popt_iv[0]:.1f} * ln(chorus) + {popt_iv[1]:.1f}")
        print(f"    90% coverage reached at: chorus {chorus_90}")
        print(f"    95% coverage reached at: chorus {chorus_95}")

    except Exception as e:
        print(f"  Could not fit saturation curve: {e}")
        popt_iv = None

    # Marginal analysis
    print(f"\n  MARGINAL CONTRIBUTION:")
    print("  " + "-"*50)

    marginal_iv_pct = []
    for i, chorus in enumerate(growth['chorus']):
        if i == 0:
            marginal_pct = growth['iv_coverage'][0]
        else:
            marginal_pct = growth['iv_coverage'][i] - growth['iv_coverage'][i-1]
        marginal_iv_pct.append(marginal_pct)

        label = f"{chorus}+" if chorus == 6 else str(chorus)
        bar = '█' * int(marginal_pct * 2)
        print(f"    Chorus {label}: +{marginal_pct:>5.1f}% {bar}")

    return marginal_iv_pct


def create_visualizations(growth: dict, tune_growth_df: pd.DataFrame,
                          late_df: pd.DataFrame, marginal: list):
    """Generate all visualizations."""
    print("\nGenerating visualizations...")

    choruses = growth['chorus']

    # 1. Cumulative growth curves
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    ax.plot(choruses, growth['cumulative_ivs'], 'o-', linewidth=2, markersize=8, color='steelblue')
    ax.set_xlabel('Chorus Number', fontsize=12)
    ax.set_ylabel('Cumulative Unique IVs', fontsize=12)
    ax.set_title('Interval Vector Vocabulary Growth', fontsize=14)
    ax.set_xticks(choruses)
    ax.set_xticklabels([f"{c}+" if c == 6 else str(c) for c in choruses])
    ax.grid(True, alpha=0.3)

    # Add percentage labels
    for i, (x, y) in enumerate(zip(choruses, growth['cumulative_ivs'])):
        ax.annotate(f"{growth['iv_coverage'][i]:.0f}%", (x, y),
                   textcoords="offset points", xytext=(0, 10), ha='center', fontsize=10)

    ax = axes[1]
    ax.plot(choruses, growth['cumulative_edges'], 'o-', linewidth=2, markersize=8, color='darkorange')
    ax.set_xlabel('Chorus Number', fontsize=12)
    ax.set_ylabel('Cumulative Unique Transitions', fontsize=12)
    ax.set_title('Transition Vocabulary Growth', fontsize=14)
    ax.set_xticks(choruses)
    ax.set_xticklabels([f"{c}+" if c == 6 else str(c) for c in choruses])
    ax.grid(True, alpha=0.3)

    for i, (x, y) in enumerate(zip(choruses, growth['cumulative_edges'])):
        ax.annotate(f"{growth['edge_coverage'][i]:.0f}%", (x, y),
                   textcoords="offset points", xytext=(0, 10), ha='center', fontsize=10)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'cumulative_growth.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/cumulative_growth.png")

    # 2. Marginal growth bars
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    bars = ax.bar(choruses, growth['new_ivs'], color='steelblue', edgecolor='black', alpha=0.8)
    ax.set_xlabel('Chorus Number', fontsize=12)
    ax.set_ylabel('New IVs Introduced', fontsize=12)
    ax.set_title('Marginal IV Growth Per Chorus', fontsize=14)
    ax.set_xticks(choruses)
    ax.set_xticklabels([f"{c}+" if c == 6 else str(c) for c in choruses])
    ax.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar, val in zip(bars, growth['new_ivs']):
        ax.annotate(str(val), (bar.get_x() + bar.get_width()/2, bar.get_height()),
                   ha='center', va='bottom', fontsize=11)

    ax = axes[1]
    bars = ax.bar(choruses, growth['new_edges'], color='darkorange', edgecolor='black', alpha=0.8)
    ax.set_xlabel('Chorus Number', fontsize=12)
    ax.set_ylabel('New Transitions Introduced', fontsize=12)
    ax.set_title('Marginal Transition Growth Per Chorus', fontsize=14)
    ax.set_xticks(choruses)
    ax.set_xticklabels([f"{c}+" if c == 6 else str(c) for c in choruses])
    ax.grid(True, alpha=0.3, axis='y')

    for bar, val in zip(bars, growth['new_edges']):
        ax.annotate(str(val), (bar.get_x() + bar.get_width()/2, bar.get_height()),
                   ha='center', va='bottom', fontsize=11)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'marginal_growth.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/marginal_growth.png")

    # 3. Per-tune chorus 1 coverage histogram
    if len(tune_growth_df) > 0:
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.hist(tune_growth_df['chorus_1_coverage'], bins=15, edgecolor='black',
                alpha=0.7, color='steelblue')
        ax.axvline(x=tune_growth_df['chorus_1_coverage'].mean(), color='red',
                  linestyle='--', linewidth=2, label=f"Mean: {tune_growth_df['chorus_1_coverage'].mean():.1f}%")
        ax.axvline(x=tune_growth_df['chorus_1_coverage'].median(), color='orange',
                  linestyle='--', linewidth=2, label=f"Median: {tune_growth_df['chorus_1_coverage'].median():.1f}%")

        ax.set_xlabel('Chorus 1 Vocabulary Coverage (%)', fontsize=12)
        ax.set_ylabel('Number of Tunes', fontsize=12)
        ax.set_title('Distribution of Chorus 1 Vocabulary Coverage Across Tunes', fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'per_tune_coverage.png', dpi=150)
        plt.close()
        print(f"  Saved: {PLOTS_DIR}/per_tune_coverage.png")

    # 4. Coverage waterfall
    fig, ax = plt.subplots(figsize=(12, 6))

    cumulative = 0
    colors = plt.cm.Blues(np.linspace(0.3, 0.9, len(marginal)))

    for i, (chorus, marg) in enumerate(zip(choruses, marginal)):
        label = f"Chorus {chorus}+" if chorus == 6 else f"Chorus {chorus}"
        ax.bar(i, marg, bottom=cumulative, color=colors[i], edgecolor='black',
               label=f"{label}: +{marg:.1f}%")

        # Add percentage label in middle of bar
        if marg > 3:
            ax.annotate(f"+{marg:.1f}%", (i, cumulative + marg/2),
                       ha='center', va='center', fontsize=10, fontweight='bold')

        cumulative += marg

    ax.set_ylabel('Cumulative Coverage (%)', fontsize=12)
    ax.set_xlabel('Chorus', fontsize=12)
    ax.set_title('Vocabulary Coverage Waterfall', fontsize=14)
    ax.set_xticks(range(len(choruses)))
    ax.set_xticklabels([f"{c}+" if c == 6 else str(c) for c in choruses])
    ax.set_ylim(0, 105)
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'coverage_waterfall.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/coverage_waterfall.png")

    # 5. Late vocabulary complexity distribution
    if len(late_df) > 0:
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.scatter(late_df['first_chorus'], late_df['iv_sum'],
                  s=late_df['total_count']*10, alpha=0.6, c=late_df['tunes'],
                  cmap='viridis', edgecolors='black', linewidth=0.5)

        ax.set_xlabel('First Appearance (Chorus)', fontsize=12)
        ax.set_ylabel('IV Complexity (sum)', fontsize=12)
        ax.set_title('Late-Appearing IVs: When vs Complexity\n(size=frequency, color=tune spread)',
                    fontsize=14)
        ax.grid(True, alpha=0.3)

        plt.colorbar(ax.collections[0], label='Number of Tunes')
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'late_vocabulary_scatter.png', dpi=150)
        plt.close()
        print(f"  Saved: {PLOTS_DIR}/late_vocabulary_scatter.png")


def export_results(growth: dict, tune_growth_df: pd.DataFrame, late_df: pd.DataFrame):
    """Export analysis results to CSV."""

    # Corpus growth
    growth_df = pd.DataFrame(growth)
    growth_df.to_csv('vocabulary_growth.csv', index=False)
    print(f"\nExported: vocabulary_growth.csv")

    # Per-tune growth
    if len(tune_growth_df) > 0:
        tune_growth_df.to_csv('tune_growth.csv', index=False)
        print(f"Exported: tune_growth.csv")

    # Late vocabulary
    if len(late_df) > 0:
        late_df.to_csv('late_vocabulary.csv', index=False)
        print(f"Exported: late_vocabulary.csv")


def print_summary(growth: dict, tune_growth_df: pd.DataFrame):
    """Print final summary."""
    print("\n" + "="*70)
    print("SUMMARY: DOES PARKER'S VOCABULARY EXPAND?")
    print("="*70)

    chorus_1_iv_pct = growth['iv_coverage'][0]
    chorus_1_edge_pct = growth['edge_coverage'][0]

    print(f"\n  CHORUS 1 CONTAINS:")
    print(f"    {chorus_1_iv_pct:.1f}% of IV vocabulary")
    print(f"    {chorus_1_edge_pct:.1f}% of transition vocabulary")

    print(f"\n  MARGINAL GROWTH:")
    for i, chorus in enumerate(growth['chorus'][1:], 1):
        iv_gain = growth['iv_coverage'][i] - growth['iv_coverage'][i-1]
        label = f"{chorus}+" if chorus == 6 else str(chorus)
        print(f"    Chorus {label}: +{iv_gain:.1f}% IVs")

    # Interpretation
    print(f"\n  INTERPRETATION:")

    if chorus_1_iv_pct >= 80:
        print("    → FRONT-LOADED: Parker deploys most vocabulary immediately")
    elif chorus_1_iv_pct >= 60:
        print("    → MODERATE EXPANSION: Significant growth after chorus 1")
    else:
        print("    → STRONG EXPANSION: Major vocabulary expansion across choruses")

    # Per-tune variance
    if len(tune_growth_df) > 0:
        std = tune_growth_df['chorus_1_coverage'].std()
        if std > 15:
            print(f"    → HIGH VARIANCE across tunes (std={std:.1f}%) - tune-dependent strategy")
        else:
            print(f"    → LOW VARIANCE across tunes (std={std:.1f}%) - consistent strategy")


def main():
    print("Parker Corpus: Vocabulary Expansion Analysis")
    print("="*70)

    # Load data
    df = load_and_prepare_data(INPUT_CSV)

    # Extract transitions
    trans_df = extract_transitions(df)
    print(f"\nExtracted {len(trans_df)} transitions")

    # Corpus-level growth
    growth = compute_corpus_growth(df, trans_df)

    # Per-tune growth
    tune_growth_df = compute_per_tune_growth(df)

    # Late vocabulary analysis
    late_df = analyze_late_vocabulary(df, trans_df)

    # Saturation analysis
    marginal = analyze_saturation(growth)

    # Summary
    print_summary(growth, tune_growth_df)

    # Visualizations
    create_visualizations(growth, tune_growth_df, late_df, marginal)

    # Export
    export_results(growth, tune_growth_df, late_df)

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nOutputs in {PLOTS_DIR}/:")
    print("  - cumulative_growth.png")
    print("  - marginal_growth.png")
    print("  - per_tune_coverage.png")
    print("  - coverage_waterfall.png")
    print("  - late_vocabulary_scatter.png")


if __name__ == '__main__':
    main()
