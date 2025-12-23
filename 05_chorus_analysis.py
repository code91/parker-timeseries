#!/usr/bin/env python3
"""
4_form_analysis.py
Structural analysis of Parker solos: shape curves, cross-chorus comparison,
form-normalized overlays, and anomaly detection.

Questions addressed:
1. Solo "shape" — does complexity build toward bridge? Decay at phrase ends?
2. Cross-chorus comparison — same position, different choruses
3. Form-normalized overlay — multiple tunes on 0-1 x-axis
4. Anomaly detection — where does Parker break his own patterns?
"""

import subprocess
import sys

for pkg in ['pandas', 'numpy', 'matplotlib', 'scipy']:
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

INPUT_CSV = 'parker_timeseries.csv'
PLOTS_DIR = Path('05_analysis_plots')
PLOTS_DIR.mkdir(exist_ok=True)

# Standard form lengths (in measures)
FORM_LENGTHS = {
    'blues': 12,
    'rhythm': 32,  # Rhythm changes (AABA)
    'standard': 32  # Most AABA standards
}


def load_data(path: str) -> pd.DataFrame:
    """Load timeseries data."""
    df = pd.read_csv(path)
    df = df.dropna(subset=['timestamp_ms'])
    print(f"Loaded {len(df)} segments from {len(df['tune'].unique())} tunes")
    return df


def infer_form_length(df_tune: pd.DataFrame) -> int:
    """Infer form length from max measure number."""
    max_measure = df_tune['measure'].max()
    
    # Common form lengths
    if max_measure <= 24:
        return 12  # Blues
    elif max_measure <= 48:
        return 32  # Standard
    elif max_measure <= 72:
        # Could be 2 choruses of blues or 1.5 of standard
        if max_measure % 12 < max_measure % 32:
            return 12
        return 32
    else:
        # Multiple choruses - find the likely form
        for form_len in [12, 32, 16]:
            if max_measure % form_len <= 4:  # Allow some slack
                return form_len
        return 32  # Default


def add_form_position(df: pd.DataFrame) -> pd.DataFrame:
    """Add normalized position within form (0-1) and chorus number."""
    df = df.copy()
    df['form_position'] = 0.0
    df['chorus_num'] = 1
    df['phrase_position'] = 0.0  # Position within 8-bar phrase
    
    for tune in df['tune'].unique():
        mask = df['tune'] == tune
        tune_df = df.loc[mask]
        
        form_len = infer_form_length(tune_df)
        
        # Compute form position (0-1 within each chorus)
        measures = tune_df['measure'].values
        beats = tune_df['beat'].values
        
        # Position in measures (fractional)
        pos_measures = measures + (beats - 1) / 4  # Assuming 4/4
        
        # Chorus number and position within chorus
        chorus_nums = (pos_measures // form_len).astype(int) + 1
        form_pos = (pos_measures % form_len) / form_len
        
        # Phrase position (8-bar phrases)
        phrase_pos = (pos_measures % 8) / 8
        
        df.loc[mask, 'form_position'] = form_pos
        df.loc[mask, 'chorus_num'] = chorus_nums
        df.loc[mask, 'phrase_position'] = phrase_pos
        df.loc[mask, 'form_length'] = form_len
    
    return df


# =============================================================================
# ANALYSIS 1: Solo Shape Curves
# =============================================================================

def analyze_solo_shape(df: pd.DataFrame):
    """
    Q1: Does complexity build toward bridge? Decay at phrase ends?
    Aggregate complexity by form position across all tunes.
    """
    print("\n" + "="*70)
    print("ANALYSIS 1: SOLO SHAPE CURVES")
    print("="*70)
    
    # Bin form position into 32 segments (like 32 bars of a standard)
    n_bins = 32
    df['form_bin'] = pd.cut(df['form_position'], bins=n_bins, labels=range(n_bins))
    
    # Aggregate metrics by form position
    shape_stats = df.groupby('form_bin').agg({
        'iv_sum': ['mean', 'std', 'count'],
        'dissonance': ['mean', 'std'],
        'iv_distance': ['mean', 'std']
    }).reset_index()
    
    shape_stats.columns = ['bin', 'iv_sum_mean', 'iv_sum_std', 'count',
                           'diss_mean', 'diss_std', 'dist_mean', 'dist_std']
    shape_stats['bin'] = shape_stats['bin'].astype(int)
    
    # Plot
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    x = shape_stats['bin'] / n_bins * 100  # Convert to percentage
    
    # IV Sum
    ax = axes[0]
    ax.plot(x, shape_stats['iv_sum_mean'], 'b-', linewidth=2, label='IV Sum')
    ax.fill_between(x, 
                    shape_stats['iv_sum_mean'] - shape_stats['iv_sum_std'],
                    shape_stats['iv_sum_mean'] + shape_stats['iv_sum_std'],
                    alpha=0.3)
    ax.set_ylabel('IV Sum (complexity)')
    ax.axvline(x=50, color='red', linestyle='--', alpha=0.5, label='Bridge (AABA)')
    ax.axvline(x=75, color='orange', linestyle='--', alpha=0.5, label='Last A')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_title('Complexity Shape Across Form Position (All Tunes Aggregated)')
    
    # Dissonance
    ax = axes[1]
    ax.plot(x, shape_stats['diss_mean'], 'orange', linewidth=2)
    ax.fill_between(x,
                    shape_stats['diss_mean'] - shape_stats['diss_std'],
                    shape_stats['diss_mean'] + shape_stats['diss_std'],
                    alpha=0.3, color='orange')
    ax.set_ylabel('Dissonance')
    ax.axvline(x=50, color='red', linestyle='--', alpha=0.5)
    ax.axvline(x=75, color='orange', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.3)
    
    # IV Distance (rate of change)
    ax = axes[2]
    ax.plot(x, shape_stats['dist_mean'], 'green', linewidth=2)
    ax.fill_between(x,
                    shape_stats['dist_mean'] - shape_stats['dist_std'],
                    shape_stats['dist_mean'] + shape_stats['dist_std'],
                    alpha=0.3, color='green')
    ax.set_ylabel('IV Distance (volatility)')
    ax.set_xlabel('Form Position (%)')
    ax.axvline(x=50, color='red', linestyle='--', alpha=0.5)
    ax.axvline(x=75, color='orange', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'solo_shape_aggregate.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/solo_shape_aggregate.png")
    
    # Phrase-level analysis (8-bar phrases)
    print("\n  Phrase-level complexity (8-bar units):")
    df['phrase_bin'] = pd.cut(df['phrase_position'], bins=8, labels=range(8))
    phrase_stats = df.groupby('phrase_bin')['iv_sum'].mean()
    
    for i, val in enumerate(phrase_stats):
        bar = '█' * int(val * 2)
        label = 'START' if i == 0 else ('END' if i == 7 else '')
        print(f"    Bar {i+1}: {val:.2f} {bar} {label}")
    
    # Statistical test: is there a significant shape?
    first_half = df[df['form_position'] < 0.5]['iv_sum']
    second_half = df[df['form_position'] >= 0.5]['iv_sum']
    t_stat, p_val = stats.ttest_ind(first_half, second_half)
    
    print(f"\n  First half vs second half complexity:")
    print(f"    First half mean:  {first_half.mean():.2f}")
    print(f"    Second half mean: {second_half.mean():.2f}")
    print(f"    t-statistic: {t_stat:.3f}, p-value: {p_val:.4f}")
    
    # Bridge analysis (50-75% for AABA forms)
    bridge = df[(df['form_position'] >= 0.5) & (df['form_position'] < 0.75)]
    non_bridge = df[(df['form_position'] < 0.5) | (df['form_position'] >= 0.75)]
    
    print(f"\n  Bridge (50-75%) vs A sections:")
    print(f"    Bridge mean complexity:     {bridge['iv_sum'].mean():.2f}")
    print(f"    A sections mean complexity: {non_bridge['iv_sum'].mean():.2f}")
    
    return shape_stats


# =============================================================================
# ANALYSIS 2: Cross-Chorus Comparison
# =============================================================================

def analyze_cross_chorus(df: pd.DataFrame):
    """
    Q2: Same structural position, different choruses.
    Compare complexity evolution across multiple choruses.
    """
    print("\n" + "="*70)
    print("ANALYSIS 2: CROSS-CHORUS COMPARISON")
    print("="*70)
    
    # Find tunes with multiple choruses
    chorus_counts = df.groupby('tune')['chorus_num'].max()
    multi_chorus_tunes = chorus_counts[chorus_counts >= 3].index.tolist()
    
    print(f"\n  Tunes with 3+ choruses: {len(multi_chorus_tunes)}")
    
    if len(multi_chorus_tunes) == 0:
        print("  No tunes with sufficient choruses for comparison")
        return
    
    # Aggregate by chorus number and form position
    df_multi = df[df['tune'].isin(multi_chorus_tunes)].copy()
    df_multi['form_bin'] = pd.cut(df_multi['form_position'], bins=16, labels=range(16))
    
    chorus_shape = df_multi.groupby(['chorus_num', 'form_bin'])['iv_sum'].mean().unstack(level=0)
    
    # Plot first 5 choruses
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(16) / 16 * 100
    colors = plt.cm.viridis(np.linspace(0, 1, min(5, chorus_shape.shape[1])))
    
    for i, (chorus, color) in enumerate(zip(chorus_shape.columns[:4], colors)):
        if chorus in chorus_shape.columns:
            # Relabel: Chorus 1 = "Head", Chorus 2 = "Chorus 1", etc.
            if int(chorus) == 1:
                label = 'Head'
            else:
                label = f'Chorus {int(chorus) - 1}'

            ax.plot(x, chorus_shape[chorus], color=color, linewidth=2,
                   label=label, marker='o', markersize=4)
    
    ax.set_xlabel('Form Position (%)')
    ax.set_ylabel('IV Sum (complexity)')
    ax.set_title('Complexity Shape: Head vs Improvised Choruses')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'cross_chorus_comparison.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/cross_chorus_comparison.png")

    # Plot only Head (Chorus 1) vs Chorus 1 (Chorus 2)
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(16) / 16 * 100

    # Only plot first two choruses
    if 1 in chorus_shape.columns and 2 in chorus_shape.columns:
        # Head (original Chorus 1)
        ax.plot(x, chorus_shape[1], color='#e74c3c', linewidth=2.5,
               label='Head (composed melody)', marker='o', markersize=5)

        # Chorus 1 (original Chorus 2)
        ax.plot(x, chorus_shape[2], color='#3498db', linewidth=2.5,
               label='Chorus 1 (first improvisation)', marker='o', markersize=5)

        ax.set_xlabel('Form Position (%)', fontsize=12)
        ax.set_ylabel('IV Sum (complexity)', fontsize=12)
        ax.set_title('Head vs First Improvised Chorus: Complexity Comparison', fontsize=14, fontweight='bold')
        ax.legend(fontsize=11, loc='upper right')
        ax.grid(True, alpha=0.3)

        # Optional: Add mean lines
        head_mean = chorus_shape[1].mean()
        improv_mean = chorus_shape[2].mean()
        ax.axhline(y=head_mean, color='#e74c3c', linestyle='--', alpha=0.5, linewidth=1)
        ax.axhline(y=improv_mean, color='#3498db', linestyle='--', alpha=0.5, linewidth=1)

        # Add text showing means
        ax.text(0.02, 0.98, f'Head mean: {head_mean:.2f}\nChorus 1 mean: {improv_mean:.2f}\nDifference: +{improv_mean - head_mean:.2f}',
                transform=ax.transAxes, fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'cross_chorus_comparison_head_1.png', dpi=150)
        plt.close()
        print(f"  Saved: {PLOTS_DIR}/cross_chorus_comparison_head_1.png")
    else:
        print("  Insufficient data for Head vs Chorus 1 comparison")
    
    # Statistical comparison: does complexity increase with chorus number?
    chorus_means = df_multi.groupby('chorus_num')['iv_sum'].mean()
    print("\n  Mean complexity by chorus:")
    for chorus, mean in chorus_means.head(6).items():
        bar = '█' * int(mean * 2)

        # Relabel for output
        if int(chorus) == 1:
            label = 'Head'
        else:
            label = f'Chorus {int(chorus) - 1}'

        print(f"    {label:12s}: {mean:.2f} {bar}")
    
    # Correlation between chorus number and complexity
    corr = df_multi[['chorus_num', 'iv_sum']].corr().iloc[0, 1]
    print(f"\n  Correlation (chorus # vs complexity): {corr:.3f}")
    print(f"  Note: Includes head melody, which is simpler by design")

    # Compute correlation excluding head
    df_improv_only = df_multi[df_multi['chorus_num'] > 1].copy()
    if len(df_improv_only) > 0:
        corr_improv = df_improv_only[['chorus_num', 'iv_sum']].corr().iloc[0, 1]
        print(f"  Correlation (improvisation only): {corr_improv:.3f}")
    return chorus_shape


# =============================================================================
# ANALYSIS 3: Form-Normalized Overlay
# =============================================================================

def analyze_form_overlay(df: pd.DataFrame):
    """
    Q3: Overlay multiple tunes on normalized 0-1 x-axis.
    """
    print("\n" + "="*70)
    print("ANALYSIS 3: FORM-NORMALIZED OVERLAY")
    print("="*70)
    
    # Normalize each tune to 0-1 based on timestamp
    df = df.copy()
    df['time_normalized'] = 0.0
    
    for tune in df['tune'].unique():
        mask = df['tune'] == tune
        t = df.loc[mask, 'timestamp_ms'].values
        t_norm = (t - t.min()) / (t.max() - t.min() + 1e-6)
        df.loc[mask, 'time_normalized'] = t_norm
    
    # Select representative tunes (mix of complexity levels)
    tune_complexity = df.groupby('tune')['iv_sum'].mean().sort_values()
    
    # Pick 5 tunes: 2 simple, 1 medium, 2 complex
    n_tunes = len(tune_complexity)
    selected = [
        tune_complexity.index[0],  # Simplest
        tune_complexity.index[n_tunes // 4],
        tune_complexity.index[n_tunes // 2],  # Medium
        tune_complexity.index[3 * n_tunes // 4],
        tune_complexity.index[-1]  # Most complex
    ]
    
    # Get tune names
    tune_names = df.groupby('tune').first().reset_index()[['tune']]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    colors = plt.cm.RdYlBu(np.linspace(0, 1, len(selected)))
    
    for tune, color in zip(selected, colors):
        tune_df = df[df['tune'] == tune].sort_values('time_normalized')
        
        # Smooth with rolling window
        if len(tune_df) > 10:
            smoothed = tune_df['iv_sum'].rolling(window=5, center=True).mean()
        else:
            smoothed = tune_df['iv_sum']
        
        ax.plot(tune_df['time_normalized'] * 100, smoothed, 
               color=color, linewidth=1.5, alpha=0.8, label=tune[:25])
    
    # Add aggregate mean
    df['time_bin'] = pd.cut(df['time_normalized'], bins=50, labels=range(50))
    agg_mean = df.groupby('time_bin')['iv_sum'].mean()
    ax.plot(np.arange(50) * 2, agg_mean.values, 'k-', linewidth=3, 
           label='Corpus Mean', alpha=0.9)
    
    ax.set_xlabel('Normalized Time Position (%)')
    ax.set_ylabel('IV Sum (complexity)')
    ax.set_title('Form-Normalized Complexity Overlay')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'form_normalized_overlay.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/form_normalized_overlay.png")
    
    # Compute solo "arc" statistics
    print("\n  Solo arc analysis (normalized time):")
    
    early = df[df['time_normalized'] < 0.33]['iv_sum'].mean()
    middle = df[(df['time_normalized'] >= 0.33) & (df['time_normalized'] < 0.67)]['iv_sum'].mean()
    late = df[df['time_normalized'] >= 0.67]['iv_sum'].mean()
    
    print(f"    Early (0-33%):  {early:.2f}")
    print(f"    Middle (33-67%): {middle:.2f}")
    print(f"    Late (67-100%): {late:.2f}")
    
    arc_type = "BUILD-SUSTAIN" if late > early else "PEAK-DECAY" if middle > max(early, late) else "FLAT"
    print(f"\n  Dominant arc type: {arc_type}")


# =============================================================================
# ANALYSIS 4: Anomaly Detection
# =============================================================================

def analyze_anomalies(df: pd.DataFrame):
    """
    Q4: Where does Parker break his own patterns?
    Identify statistically unusual IV transitions.
    """
    print("\n" + "="*70)
    print("ANALYSIS 4: ANOMALY DETECTION")
    print("="*70)
    
    # Build transition probability matrix
    transitions = []
    df_sorted = df.sort_values(['tune', 'timestamp_ms'])
    
    for tune in df['tune'].unique():
        tune_df = df_sorted[df_sorted['tune'] == tune]
        ivs = tune_df['iv'].tolist()
        
        for i in range(len(ivs) - 1):
            transitions.append((ivs[i], ivs[i+1]))
    
    # Count transitions
    trans_counts = Counter(transitions)
    total_trans = len(transitions)
    
    # Count source IVs
    source_counts = Counter([t[0] for t in transitions])
    
    # Compute transition probabilities
    trans_probs = {}
    for (src, dst), count in trans_counts.items():
        prob = count / source_counts[src]
        trans_probs[(src, dst)] = {
            'count': count,
            'prob': prob,
            'expected': source_counts[src] * (trans_counts.get((src, dst), 0) / total_trans)
        }
    
    # Find rare transitions (low probability given the source)
    rare_transitions = []
    for (src, dst), info in trans_probs.items():
        if info['count'] >= 2:  # At least 2 occurrences (not just noise)
            if info['prob'] < 0.05:  # Less than 5% probability
                rare_transitions.append({
                    'source': src,
                    'target': dst,
                    'count': info['count'],
                    'prob': info['prob']
                })
    
    rare_transitions.sort(key=lambda x: x['prob'])
    
    print(f"\n  Total unique transitions: {len(trans_counts)}")
    print(f"  Total transition instances: {total_trans}")
    
    print("\n  RARE TRANSITIONS (prob < 5%, count >= 2):")
    print("  " + "-"*60)
    
    for t in rare_transitions[:15]:
        print(f"    {t['source']} → {t['target']}: {t['count']}x ({t['prob']:.1%})")
    
    # Find high-velocity moments (outliers in iv_distance)
    threshold = df['iv_distance'].mean() + 2 * df['iv_distance'].std()
    outliers = df[df['iv_distance'] > threshold].copy()
    
    print(f"\n  HIGH-VELOCITY MOMENTS (iv_distance > {threshold:.2f}):")
    print(f"  Found {len(outliers)} anomalous transitions ({len(outliers)/len(df)*100:.1f}%)")
    
    if len(outliers) > 0:
        # Group by tune
        outlier_tunes = outliers.groupby('tune').size().sort_values(ascending=False)
        print("\n  Top tunes with anomalous transitions:")
        for tune, count in outlier_tunes.head(10).items():
            tune_total = len(df[df['tune'] == tune])
            pct = count / tune_total * 100
            print(f"    {tune[:30]}: {count} ({pct:.1f}%)")
    
    # Plot anomaly distribution
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Histogram with threshold
    ax = axes[0]
    ax.hist(df['iv_distance'], bins=40, edgecolor='black', alpha=0.7)
    ax.axvline(x=threshold, color='red', linestyle='--', linewidth=2, 
               label=f'Anomaly threshold ({threshold:.1f})')
    ax.set_xlabel('IV Distance')
    ax.set_ylabel('Frequency')
    ax.set_title('IV Distance Distribution with Anomaly Threshold')
    ax.legend()
    
    # Anomalies by form position
    ax = axes[1]
    if len(outliers) > 0:
        ax.hist(outliers['form_position'] * 100, bins=20, edgecolor='black', alpha=0.7, color='red')
    ax.set_xlabel('Form Position (%)')
    ax.set_ylabel('Anomaly Count')
    ax.set_title('Where Anomalies Occur in Form')
    ax.axvline(x=50, color='blue', linestyle='--', alpha=0.5, label='Bridge')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'anomaly_analysis.png', dpi=150)
    plt.close()
    print(f"\n  Saved: {PLOTS_DIR}/anomaly_analysis.png")
    
    # Save anomalies to CSV
    if len(outliers) > 0:
        outliers.to_csv('anomalies.csv', index=False)
        print(f"  Saved: anomalies.csv ({len(outliers)} rows)")
    
    return outliers, rare_transitions


def main():
    print("Parker Corpus: Form & Structural Analysis")
    print("="*70)
    
    # Load data
    df = load_data(INPUT_CSV)
    
    # Add form position
    print("\nInferring form structure...")
    df = add_form_position(df)
    
    # Run analyses
    shape_stats = analyze_solo_shape(df)
    chorus_comparison = analyze_cross_chorus(df)
    analyze_form_overlay(df)
    outliers, rare_trans = analyze_anomalies(df)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nOutputs:")
    print("  - plots_analysis/solo_shape_aggregate.png")
    print("  - plots_analysis/cross_chorus_comparison.png")
    print("  - plots_analysis/form_normalized_overlay.png")
    print("  - plots_analysis/anomaly_analysis.png")
    print("  - anomalies.csv")


if __name__ == '__main__':
    main()
