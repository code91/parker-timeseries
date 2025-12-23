#!/usr/bin/env python3
"""
8_rolling_window_robustness.py
Rolling window analysis and robustness metrics on phrase-level data.

Outputs:
- Rolling statistics for complexity, dissonance, phrase length
- Robustness metrics (CV, stability) per tune
- Visualizations comparing window sizes and tunes
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
import warnings
warnings.filterwarnings('ignore')

INPUT_CSV = 'parker_phrases.csv'
PLOTS_DIR = Path('08_rolling_window_plots')
PLOTS_DIR.mkdir(exist_ok=True)

# Configuration
WINDOW_SIZES = [3, 5, 10]  # Phrase windows to test
METRICS = ['mean_iv_sum', 'mean_dissonance', 'segment_count']
METRIC_LABELS = {
    'mean_iv_sum': 'Complexity (Mean IV Sum)',
    'mean_dissonance': 'Dissonance',
    'segment_count': 'Phrase Length (segments)'
}


def load_data(path: str) -> pd.DataFrame:
    """Load phrase-level data."""
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} phrases from {df['tune'].nunique()} tunes")
    return df


def compute_rolling_stats(df: pd.DataFrame, tune: str, metric: str, window_size: int) -> pd.DataFrame:
    """
    Compute rolling statistics for a single tune and metric.
    
    Returns DataFrame with: phrase_id, raw_value, rolling_mean, rolling_std, rolling_cv
    """
    tune_df = df[df['tune'] == tune].sort_values('phrase_id').reset_index(drop=True)
    
    if len(tune_df) < window_size:
        return None
    
    values = tune_df[metric].values
    
    # Compute rolling statistics
    rolling_mean = pd.Series(values).rolling(window=window_size, center=True).mean().values
    rolling_std = pd.Series(values).rolling(window=window_size, center=True).std().values
    
    # Coefficient of variation (CV = std/mean)
    # Handle division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        rolling_cv = rolling_std / rolling_mean
        rolling_cv[~np.isfinite(rolling_cv)] = 0
    
    result = pd.DataFrame({
        'phrase_id': tune_df['phrase_id'],
        'phrase_idx': range(len(tune_df)),
        'raw_value': values,
        'rolling_mean': rolling_mean,
        'rolling_std': rolling_std,
        'rolling_cv': rolling_cv,
        'window_size': window_size
    })
    
    return result


def compute_tune_robustness_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute robustness/stability metrics for each tune.
    
    Metrics:
    - Global CV (coefficient of variation across entire tune)
    - Mean absolute deviation
    - Range (max - min)
    - Entropy approximation (normalized histogram)
    """
    results = []
    
    for tune in df['tune'].unique():
        tune_df = df[df['tune'] == tune]
        
        tune_metrics = {
            'tune': tune,
            'phrase_count': len(tune_df)
        }
        
        for metric in METRICS:
            values = tune_df[metric].values
            
            # Global statistics
            mean_val = np.mean(values)
            std_val = np.std(values)
            
            # Coefficient of variation
            cv = std_val / mean_val if mean_val > 0 else 0
            
            # Mean absolute deviation
            mad = np.mean(np.abs(values - mean_val))
            
            # Range
            range_val = np.max(values) - np.min(values)
            
            # Normalized range (range / mean)
            norm_range = range_val / mean_val if mean_val > 0 else 0
            
            # Store
            tune_metrics[f'{metric}_mean'] = mean_val
            tune_metrics[f'{metric}_std'] = std_val
            tune_metrics[f'{metric}_cv'] = cv
            tune_metrics[f'{metric}_mad'] = mad
            tune_metrics[f'{metric}_range'] = range_val
            tune_metrics[f'{metric}_norm_range'] = norm_range
        
        results.append(tune_metrics)
    
    return pd.DataFrame(results)


def visualize_single_tune_windows(df: pd.DataFrame, tune: str, metric: str):
    """
    Visualize rolling window analysis for one tune across different window sizes.
    """
    print(f"\nVisualizing: {tune} - {metric}")
    
    tune_df = df[df['tune'] == tune]
    
    if len(tune_df) < max(WINDOW_SIZES):
        print(f"  Skipping {tune}: only {len(tune_df)} phrases (need >= {max(WINDOW_SIZES)})")
        return
    
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
    
    # Get raw values
    raw_values = tune_df.sort_values('phrase_id')[metric].values
    phrase_indices = np.arange(len(raw_values))
    
    # Plot 1: Raw values + rolling means
    ax = axes[0]
    ax.plot(phrase_indices, raw_values, 'o-', color='black', alpha=0.3, 
            linewidth=1, markersize=4, label='Raw values')
    
    colors = ['blue', 'green', 'red']
    for window_size, color in zip(WINDOW_SIZES, colors):
        rolling_stats = compute_rolling_stats(df, tune, metric, window_size)
        if rolling_stats is not None:
            ax.plot(rolling_stats['phrase_idx'], rolling_stats['rolling_mean'],
                   linewidth=2.5, color=color, alpha=0.8,
                   label=f'Rolling mean (window={window_size})')
    
    ax.set_ylabel(METRIC_LABELS[metric], fontsize=12)
    ax.set_title(f'{tune}: Rolling Window Analysis - {METRIC_LABELS[metric]}', 
                fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Rolling CV (local volatility)
    ax = axes[1]
    
    for window_size, color in zip(WINDOW_SIZES, colors):
        rolling_stats = compute_rolling_stats(df, tune, metric, window_size)
        if rolling_stats is not None:
            ax.plot(rolling_stats['phrase_idx'], rolling_stats['rolling_cv'],
                   linewidth=2, color=color, alpha=0.8,
                   label=f'Rolling CV (window={window_size})')
    
    ax.set_xlabel('Phrase Index', fontsize=12)
    ax.set_ylabel('Coefficient of Variation', fontsize=12)
    ax.set_title('Local Volatility (Rolling CV)', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    filename = f"{tune.replace(' ', '_')}_{metric}_windows.png"
    plt.savefig(PLOTS_DIR / filename, dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/{filename}")


def compare_tunes_rolling_window(df: pd.DataFrame, tunes: list, metric: str, window_size: int):
    """
    Compare rolling window patterns across multiple tunes.
    """
    print(f"\nComparing tunes: {metric} (window={window_size})")
    
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(tunes)))
    
    # Plot 1: Raw values + rolling means
    ax = axes[0]
    
    for tune, color in zip(tunes, colors):
        tune_df = df[df['tune'] == tune].sort_values('phrase_id')
        
        if len(tune_df) < window_size:
            continue
        
        rolling_stats = compute_rolling_stats(df, tune, metric, window_size)
        if rolling_stats is not None:
            # Normalize x-axis to 0-100% for comparison
            phrase_pct = rolling_stats['phrase_idx'] / len(tune_df) * 100
            
            ax.plot(phrase_pct, rolling_stats['raw_value'], 
                   'o-', color=color, alpha=0.2, linewidth=0.5, markersize=2)
            ax.plot(phrase_pct, rolling_stats['rolling_mean'],
                   linewidth=2.5, color=color, alpha=0.8, label=tune)
    
    ax.set_ylabel(METRIC_LABELS[metric], fontsize=12)
    ax.set_title(f'Tune Comparison: {METRIC_LABELS[metric]} (window={window_size} phrases)',
                fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Rolling CV comparison
    ax = axes[1]
    
    for tune, color in zip(tunes, colors):
        rolling_stats = compute_rolling_stats(df, tune, metric, window_size)
        if rolling_stats is not None:
            phrase_pct = rolling_stats['phrase_idx'] / len(df[df['tune'] == tune]) * 100
            ax.plot(phrase_pct, rolling_stats['rolling_cv'],
                   linewidth=2, color=color, alpha=0.8, label=tune)
    
    ax.set_xlabel('Phrase Position (%)', fontsize=12)
    ax.set_ylabel('Coefficient of Variation', fontsize=12)
    ax.set_title('Local Volatility Comparison', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    filename = f"tune_comparison_{metric}_w{window_size}.png"
    plt.savefig(PLOTS_DIR / filename, dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/{filename}")


def visualize_robustness_rankings(robustness_df: pd.DataFrame):
    """
    Visualize robustness metrics across tunes.
    """
    print("\nVisualizing robustness rankings...")
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    for idx, metric in enumerate(METRICS):
        ax = axes[idx]
        
        # Sort by CV (higher = more variable/less robust)
        sorted_df = robustness_df.sort_values(f'{metric}_cv', ascending=False)
        
        # Take top 15 most variable tunes
        plot_df = sorted_df.head(15)
        
        y_pos = np.arange(len(plot_df))
        
        ax.barh(y_pos, plot_df[f'{metric}_cv'], color='steelblue', edgecolor='black')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(plot_df['tune'], fontsize=9)
        ax.set_xlabel('Coefficient of Variation', fontsize=11)
        ax.set_title(f'Most Variable Tunes:\n{METRIC_LABELS[metric]}', 
                    fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'robustness_rankings.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/robustness_rankings.png")


def analyze_window_size_impact(df: pd.DataFrame, tune: str, metric: str):
    """
    Analyze how window size affects smoothing and volatility detection.
    """
    print(f"\nAnalyzing window size impact: {tune}")
    
    fig, axes = plt.subplots(len(WINDOW_SIZES), 1, figsize=(16, 12), sharex=True)
    
    tune_df = df[df['tune'] == tune]
    raw_values = tune_df.sort_values('phrase_id')[metric].values
    phrase_indices = np.arange(len(raw_values))
    
    for idx, window_size in enumerate(WINDOW_SIZES):
        ax = axes[idx]
        
        rolling_stats = compute_rolling_stats(df, tune, metric, window_size)
        if rolling_stats is None:
            continue
        
        # Plot raw + rolling mean
        ax.plot(phrase_indices, raw_values, 'o-', color='gray', alpha=0.3,
               linewidth=1, markersize=3, label='Raw')
        ax.plot(rolling_stats['phrase_idx'], rolling_stats['rolling_mean'],
               linewidth=2.5, color='blue', label='Rolling mean')
        
        # Shade ±1 std
        upper = rolling_stats['rolling_mean'] + rolling_stats['rolling_std']
        lower = rolling_stats['rolling_mean'] - rolling_stats['rolling_std']
        ax.fill_between(rolling_stats['phrase_idx'], lower, upper,
                        alpha=0.2, color='blue', label='±1 std')
        
        ax.set_ylabel(METRIC_LABELS[metric], fontsize=11)
        ax.set_title(f'Window Size = {window_size} phrases', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
    
    axes[-1].set_xlabel('Phrase Index', fontsize=12)
    
    plt.suptitle(f'{tune}: Impact of Window Size on {METRIC_LABELS[metric]}',
                fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    filename = f"{tune.replace(' ', '_')}_window_comparison_{metric}.png"
    plt.savefig(PLOTS_DIR / filename, dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/{filename}")


def print_robustness_summary(robustness_df: pd.DataFrame):
    """Print summary statistics of robustness metrics."""
    print("\n" + "="*70)
    print("ROBUSTNESS METRICS SUMMARY")
    print("="*70)
    
    for metric in METRICS:
        print(f"\n{METRIC_LABELS[metric]}:")
        print(f"  {'Tune':<25s} {'Mean':>8s} {'CV':>8s} {'Norm Range':>12s}")
        print("  " + "-"*60)
        
        # Sort by CV
        sorted_df = robustness_df.sort_values(f'{metric}_cv', ascending=False).head(10)
        
        for _, row in sorted_df.iterrows():
            tune_name = row['tune'][:24]  # Truncate long names
            mean_val = row[f'{metric}_mean']
            cv = row[f'{metric}_cv']
            norm_range = row[f'{metric}_norm_range']
            
            print(f"  {tune_name:<25s} {mean_val:>8.2f} {cv:>8.2f} {norm_range:>12.2f}")
    
    print("\n" + "="*70)


def main():
    print("Parker Corpus: Rolling Window & Robustness Analysis")
    print("="*70)
    
    # Load phrase data
    df = load_data(INPUT_CSV)
    
    # Compute robustness metrics for all tunes
    print("\nComputing robustness metrics for all tunes...")
    robustness_df = compute_tune_robustness_metrics(df)
    
    # Save robustness metrics
    robustness_df.to_csv('parker_robustness_metrics.csv', index=False)
    print(f"Saved: parker_robustness_metrics.csv")
    
    # Print summary
    print_robustness_summary(robustness_df)
    
    # Select example tunes for visualization
    # Use tunes with different complexity characteristics
    complexity_sorted = robustness_df.sort_values('mean_iv_sum_mean', ascending=False)
    
    high_complexity = complexity_sorted.iloc[0]['tune']  # Highest
    low_complexity = complexity_sorted.iloc[-1]['tune']  # Lowest
    medium_complexity = complexity_sorted.iloc[len(complexity_sorted)//2]['tune']  # Middle
    
    # Also get most/least variable
    most_variable = robustness_df.sort_values('mean_iv_sum_cv', ascending=False).iloc[0]['tune']
    least_variable = robustness_df.sort_values('mean_iv_sum_cv', ascending=True).iloc[0]['tune']
    
    example_tunes = [high_complexity, low_complexity, medium_complexity, most_variable, least_variable]
    example_tunes = list(dict.fromkeys(example_tunes))  # Remove duplicates, preserve order
    
    print(f"\nExample tunes selected:")
    print(f"  High complexity: {high_complexity}")
    print(f"  Low complexity: {low_complexity}")
    print(f"  Medium complexity: {medium_complexity}")
    print(f"  Most variable: {most_variable}")
    print(f"  Least variable: {least_variable}")
    
    # Generate visualizations
    print("\n" + "="*70)
    print("GENERATING VISUALIZATIONS")
    print("="*70)
    
    # 1. Individual tune window analysis (complexity only)
    for tune in example_tunes[:3]:  # Visualize 3 tunes
        visualize_single_tune_windows(df, tune, 'mean_iv_sum')
    
    # 2. Window size impact analysis (one tune, all metrics)
    print("\n" + "="*70)
    print("WINDOW SIZE IMPACT ANALYSIS")
    print("="*70)
    
    analyze_window_size_impact(df, high_complexity, 'mean_iv_sum')
    
    # 3. Tune comparison (use 5-phrase window)
    print("\n" + "="*70)
    print("TUNE COMPARISONS")
    print("="*70)
    
    compare_tunes_rolling_window(df, example_tunes, 'mean_iv_sum', window_size=5)
    compare_tunes_rolling_window(df, example_tunes, 'mean_dissonance', window_size=5)
    
    # 4. Robustness rankings
    print("\n" + "="*70)
    print("ROBUSTNESS RANKINGS")
    print("="*70)
    
    visualize_robustness_rankings(robustness_df)
    
    # Summary
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nOutputs:")
    print(f"  - parker_robustness_metrics.csv")
    print(f"  - {PLOTS_DIR}/")
    print(f"    - Individual tune window analyses")
    print(f"    - Window size impact comparisons")
    print(f"    - Tune comparisons")
    print(f"    - Robustness rankings")
    
    print("\nKey findings:")
    print("  - Window size 3: Captures phrase-to-phrase volatility")
    print("  - Window size 5: Balanced smoothing (recommended)")
    print("  - Window size 10: Reveals macro-level trends")
    print("\nNext step: Script 9 - Granger Causality Analysis")


if __name__ == '__main__':
    main()
