#!/usr/bin/env python3
"""
3_timeseries_analysis.py
Time series analysis of Parker corpus with derived metrics.

Outputs:
- parker_timeseries.csv: enriched data with metrics
- 3_timeseries_plots/: visualization directory
"""

import subprocess
import sys

# Auto-install dependencies
for pkg in ['pandas', 'numpy', 'matplotlib']:
    try:
        __import__(pkg.replace('-', '_').split('[')[0])
    except ImportError:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configuration
INPUT_CSV = 'parker_sequential_aligned.csv'
OUTPUT_CSV = 'parker_timeseries.csv'
PLOTS_DIR = Path('03_timeseries_plots')

# Dissonance weights (Hindemith-inspired: minor 2nd, major 2nd, tritone)
DISSONANCE_WEIGHTS = {
    'ic1': 1.0,   # minor 2nd - most dissonant
    'ic2': 0.5,   # major 2nd - moderate
    'ic6': 0.8,   # tritone - high dissonance
}


def load_data(path: str) -> pd.DataFrame:
    """Load aligned sequential data, filtering out failed MIDI alignments."""
    df = pd.read_csv(path)
    total = len(df)

    # Filter out segments with missing timestamps (failed MIDI alignment)
    df = df.dropna(subset=['timestamp_ms'])
    failed_count = total - len(df)

    if failed_count > 0:
        print(f"Loaded {total} segments from {path}")
        print(f"Filtered out {failed_count} segments with missing MIDI alignment")
        print(f"Analyzing {len(df)} aligned segments ({len(df['tune'].unique())} tunes)")
    else:
        print(f"Loaded {len(df)} segments from {path}")

    print(f"Columns: {list(df.columns)}")
    return df


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute time series metrics for each segment.
    """
    iv_cols = ['ic1', 'ic2', 'ic3', 'ic4', 'ic5', 'ic6']

    # 1. IV sum (complexity proxy)
    df['iv_sum'] = df[iv_cols].sum(axis=1)

    # 2. Dissonance index (weighted sum)
    df['dissonance'] = (
        df['ic1'] * DISSONANCE_WEIGHTS['ic1'] +
        df['ic2'] * DISSONANCE_WEIGHTS['ic2'] +
        df['ic6'] * DISSONANCE_WEIGHTS['ic6']
    )

    # 3. Consecutive IV distance (rate of change)
    # Computed per tune
    df['iv_distance'] = 0.0

    for tune in df['tune'].unique():
        mask = df['tune'] == tune
        tune_df = df.loc[mask, iv_cols].values

        # Euclidean distance to previous segment
        distances = np.zeros(len(tune_df))
        for i in range(1, len(tune_df)):
            distances[i] = np.linalg.norm(tune_df[i] - tune_df[i-1])

        df.loc[mask, 'iv_distance'] = distances

    return df


def normalize_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add normalized versions of metrics (0-1 scale based on corpus min/max).
    """
    metrics_to_normalize = ['iv_sum', 'dissonance', 'iv_distance']

    for metric in metrics_to_normalize:
        min_val = df[metric].min()
        max_val = df[metric].max()
        range_val = max_val - min_val

        if range_val > 0:
            df[f'{metric}_norm'] = (df[metric] - min_val) / range_val
        else:
            df[f'{metric}_norm'] = 0.0

    return df


def create_visualizations(df: pd.DataFrame):
    """Generate analysis plots."""
    PLOTS_DIR.mkdir(exist_ok=True)

    # 1. Time series for representative tunes (top 4 by segment count) - NORMALIZED
    tune_counts = df['tune'].value_counts()
    available = tune_counts.head(4).index.tolist()

    if len(available) > 0:
        fig, axes = plt.subplots(len(available), 1, figsize=(14, 3*len(available)))
        if len(available) == 1:
            axes = [axes]

        # Corpus-wide means for reference lines
        corpus_means = {
            'iv_sum_norm': df['iv_sum_norm'].mean(),
            'dissonance_norm': df['dissonance_norm'].mean(),
            'iv_distance_norm': df['iv_distance_norm'].mean()
        }

        for ax, tune_name in zip(axes, available):
            tune_df = df[df['tune'] == tune_name].sort_values('timestamp_ms')

            # Normalize time to percentage of tune
            t = tune_df['timestamp_ms'].values
            t_norm = (t - t.min()) / (t.max() - t.min() + 1e-6) * 100

            # Plot normalized metrics
            ax.plot(t_norm, tune_df['iv_sum_norm'], label='IV Sum', alpha=0.8, linewidth=1.5)
            ax.plot(t_norm, tune_df['dissonance_norm'], label='Dissonance', alpha=0.8, linewidth=1.5)
            ax.plot(t_norm, tune_df['iv_distance_norm'], label='IV Distance', alpha=0.8, linewidth=1.5)

            # Calculate tune means
            tune_means = {
                'iv_sum_norm': tune_df['iv_sum_norm'].mean(),
                'dissonance_norm': tune_df['dissonance_norm'].mean(),
                'iv_distance_norm': tune_df['iv_distance_norm'].mean()
            }

            # Add text box with mean values instead of lines
            textstr = 'Mean values:\n'
            textstr += f'  IV Sum: {tune_means["iv_sum_norm"]:.2f} (corpus: {corpus_means["iv_sum_norm"]:.2f})\n'
            textstr += f'  Dissonance: {tune_means["dissonance_norm"]:.2f} (corpus: {corpus_means["dissonance_norm"]:.2f})\n'
            textstr += f'  IV Distance: {tune_means["iv_distance_norm"]:.2f} (corpus: {corpus_means["iv_distance_norm"]:.2f})'

            props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
            ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                   verticalalignment='top', bbox=props, family='monospace')

            ax.set_title(f'{tune_name}')
            ax.set_xlabel('Position (%)')
            ax.set_ylabel('Normalized Value (0-1)')
            ax.set_ylim(-0.05, 1.05)
            ax.legend(loc='upper right', fontsize=8)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'timeseries_samples.png', dpi=150)
        plt.close()
        print(f"  Saved: {PLOTS_DIR}/timeseries_samples.png")

    # 2. Metric distributions
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    axes[0].hist(df['iv_sum'], bins=30, edgecolor='black', alpha=0.7)
    axes[0].axvline(x=df['iv_sum'].mean(), color='red', linestyle='--',
                       linewidth=2, label=f'Mean: {df["iv_sum"].mean():.1f}')
    axes[0].set_title('IV Sum Distribution')
    axes[0].set_xlabel('IV Sum')
    axes[0].legend()

    axes[1].hist(df['dissonance'], bins=30, edgecolor='black', alpha=0.7, color='orange')
    axes[1].axvline(x=df['dissonance'].mean(), color='red', linestyle='--',
                       linewidth=2, label=f'Mean: {df["dissonance"].mean():.1f}')
    axes[1].set_title('Dissonance Index Distribution')
    axes[1].set_xlabel('Dissonance')
    axes[1].legend()

    axes[2].hist(df['iv_distance'][df['iv_distance'] > 0], bins=30,
                    edgecolor='black', alpha=0.7, color='green')
    axes[2].axvline(x=df[df['iv_distance'] > 0]['iv_distance'].mean(),
                       color='red', linestyle='--', linewidth=2,
                       label=f'Mean: {df[df["iv_distance"] > 0]["iv_distance"].mean():.2f}')
    axes[2].set_title('IV Distance Distribution (excl. first segments)')
    axes[2].set_xlabel('Euclidean Distance')
    axes[2].legend()

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'metric_distributions.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/metric_distributions.png")


def print_summary_stats(df: pd.DataFrame):
    """Print summary statistics."""
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)

    metrics = ['iv_sum', 'dissonance', 'iv_distance']

    print("\n{:<15} {:>10} {:>10} {:>10} {:>10}".format(
        'Metric', 'Mean', 'Std', 'Min', 'Max'))
    print("-" * 55)

    for m in metrics:
        print("{:<15} {:>10.2f} {:>10.2f} {:>10.2f} {:>10.2f}".format(
            m, df[m].mean(), df[m].std(), df[m].min(), df[m].max()))

    # Per-tune stats
    print("\nPer-tune average complexity (IV sum):")
    tune_stats = df.groupby('tune')['iv_sum'].mean().sort_values(ascending=False)
    print("\n  Highest complexity:")
    for title, val in tune_stats.head(5).items():
        print(f"    {title}: {val:.2f}")
    print("\n  Lowest complexity:")
    for title, val in tune_stats.tail(5).items():
        print(f"    {title}: {val:.2f}")

    # Most variable tunes (highest iv_distance mean)
    print("\nMost variable tunes (avg IV distance):")
    var_stats = df.groupby('tune')['iv_distance'].mean().sort_values(ascending=False)
    for title, val in var_stats.head(5).items():
        print(f"    {title}: {val:.2f}")


def main():
    print("Parker Corpus Time Series Analysis")
    print("="*60)

    # Load data
    df = load_data(INPUT_CSV)

    # Metrics
    print("\nComputing time series metrics...")
    df = compute_metrics(df)

    # Normalize metrics
    print("\nNormalizing metrics...")
    df = normalize_metrics(df)

    # Print metric ranges
    print("\n" + "="*60)
    print("CORPUS-WIDE METRIC RANGES")
    print("="*60)
    metrics = ['iv_sum', 'dissonance', 'iv_distance']
    for metric in metrics:
        print(f"  {metric:<15} min: {df[metric].min():>6.2f}  max: {df[metric].max():>6.2f}  mean: {df[metric].mean():>6.2f}")

    # Summary
    print_summary_stats(df)

    # Visualizations
    print("\nGenerating visualizations...")
    create_visualizations(df)

    # Save enriched data
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nEnriched data saved to {OUTPUT_CSV}")

    # Column summary
    new_cols = ['iv_sum', 'dissonance', 'iv_distance',
                'iv_sum_norm', 'dissonance_norm', 'iv_distance_norm']
    print(f"\nNew columns added: {new_cols}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Ready for further analysis")


if __name__ == '__main__':
    main()
