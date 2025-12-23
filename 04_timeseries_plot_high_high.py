#!/usr/bin/env python3
"""
4_compare_tunes_dtw.py
Compare two tunes using Dynamic Time Warping for alignment.
"""

import subprocess
import sys

# Auto-install DTW library
try:
    from dtaidistance import dtw
    from dtaidistance import dtw_visualisation as dtwvis
except ImportError:
    print("Installing dtaidistance...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'dtaidistance', '-q'])
    from dtaidistance import dtw
    from dtaidistance import dtw_visualisation as dtwvis

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Configuration
INPUT_CSV = 'parker_timeseries.csv'
PLOTS_DIR = Path('04_comparison_plots')
PLOTS_DIR.mkdir(exist_ok=True)


def normalize_time(df):
    """Normalize timestamps to 0-100% for a tune."""
    t = df['timestamp_ms'].values
    return (t - t.min()) / (t.max() - t.min() + 1e-6) * 100


def plot_tune_comparison_dtw(tune1_name, tune2_name):
    """Create comparison using DTW alignment."""
    
    # Load data
    df = pd.read_csv(INPUT_CSV)
    
    # Filter tunes
    tune1_df = df[df['tune'] == tune1_name].sort_values('timestamp_ms').copy()
    tune2_df = df[df['tune'] == tune2_name].sort_values('timestamp_ms').copy()
    
    if len(tune1_df) == 0:
        print(f"Tune not found: {tune1_name}")
        return
    if len(tune2_df) == 0:
        print(f"Tune not found: {tune2_name}")
        return
    
    # Normalize time
    tune1_df['t_norm'] = normalize_time(tune1_df)
    tune2_df['t_norm'] = normalize_time(tune2_df)
    
    # Extract IV sum series
    series1 = tune1_df['iv_sum_norm'].values
    series2 = tune2_df['iv_sum_norm'].values
    
    print(f"\n{tune1_name}: {len(series1)} segments")
    print(f"{tune2_name}: {len(series2)} segments")
    
    # Compute DTW
    print("\nComputing DTW alignment...")
    distance = dtw.distance(series1, series2)
    path = dtw.warping_path(series1, series2)
    
    print(f"DTW distance: {distance:.4f}")
    print(f"Warping path length: {len(path)}")
    
    # Create 4-panel visualization
    fig = plt.figure(figsize=(16, 12))
    
    # Panel 1: Individual time series for tune 1
    ax1 = plt.subplot(3, 2, 1)
    metrics = ['iv_sum_norm', 'dissonance_norm', 'iv_distance_norm']
    colors = ['#2E86AB', '#A23B72', '#F18F01']
    labels = ['IV Sum', 'Dissonance', 'IV Distance']
    
    for metric, color, label in zip(metrics, colors, labels):
        ax1.plot(tune1_df['t_norm'], tune1_df[metric], 
                label=label, color=color, alpha=0.8, linewidth=1.5)
    
    ax1.set_title(f'{tune1_name} ({len(series1)} segments)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Position (%)')
    ax1.set_ylabel('Normalized Value')
    ax1.set_ylim(-0.05, 1.05)
    ax1.legend(loc='upper right', fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Individual time series for tune 2
    ax2 = plt.subplot(3, 2, 2)
    for metric, color, label in zip(metrics, colors, labels):
        ax2.plot(tune2_df['t_norm'], tune2_df[metric], 
                label=label, color=color, alpha=0.8, linewidth=1.5)
    
    ax2.set_title(f'{tune2_name} ({len(series2)} segments)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Position (%)')
    ax2.set_ylabel('Normalized Value')
    ax2.set_ylim(-0.05, 1.05)
    ax2.legend(loc='upper right', fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: DTW alignment visualization
    ax3 = plt.subplot(3, 2, (3, 4))
    
    # Plot both series
    x1 = np.arange(len(series1))
    x2 = np.arange(len(series2))
    
    ax3.plot(x1, series1, 'o-', color='#2E86AB', label=tune1_name, linewidth=2, markersize=4, alpha=0.7)
    ax3.plot(x2, series2, 'o-', color='#E63946', label=tune2_name, linewidth=2, markersize=4, alpha=0.7)
    
    # Draw warping path connections (sample every nth to avoid clutter)
    step = max(1, len(path) // 50)  # Show max 50 connections
    for i in range(0, len(path), step):
        idx1, idx2 = path[i]
        ax3.plot([idx1, idx2], [series1[idx1], series2[idx2]], 
                'k-', alpha=0.15, linewidth=0.5)
    
    ax3.set_title(f'DTW Alignment (distance: {distance:.4f})', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Segment Index')
    ax3.set_ylabel('Normalized IV Sum')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Panel 4: Overlay with normalized time axis
    ax4 = plt.subplot(3, 2, (5, 6))
    
    ax4.plot(tune1_df['t_norm'], series1, 
            label=f'{tune1_name}', color='#2E86AB', 
            alpha=0.8, linewidth=2.5, linestyle='-')
    ax4.plot(tune2_df['t_norm'], series2, 
            label=f'{tune2_name}', color='#E63946', 
            alpha=0.8, linewidth=2.5, linestyle='-')
    
    ax4.set_title('IV Sum: Time-Normalized Overlay', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Position (%)')
    ax4.set_ylabel('Normalized IV Sum')
    ax4.set_ylim(-0.05, 1.05)
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    # Add comparison stats
    diff = series1.mean() - series2.mean()
    comparison = f"Mean IV Sum:\n"
    comparison += f"  {tune1_name[:20]}: {series1.mean():.3f}\n"
    comparison += f"  {tune2_name[:20]}: {series2.mean():.3f}\n"
    comparison += f"  Difference: {diff:+.3f}\n"
    comparison += f"DTW distance: {distance:.4f}"
    
    ax4.text(0.02, 0.98, comparison, transform=ax4.transAxes, fontsize=9,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
            family='monospace')
    
    plt.tight_layout()
    
    # Save
    filename = f"{tune1_name.replace(' ', '_')}_vs_{tune2_name.replace(' ', '_')}_DTW.png"
    filepath = PLOTS_DIR / filename
    plt.savefig(filepath, dpi=150)
    plt.close()
    
    print(f"\nSaved: {filepath}")
    
    # Print alignment statistics
    print(f"\n{tune1_name}:")
    print(f"  Mean IV Sum: {series1.mean():.3f}")
    print(f"  Std IV Sum: {series1.std():.3f}")
    
    print(f"\n{tune2_name}:")
    print(f"  Mean IV Sum: {series2.mean():.3f}")
    print(f"  Std IV Sum: {series2.std():.3f}")
    
    print(f"\nDTW Analysis:")
    print(f"  Distance: {distance:.4f}")
    print(f"  Path length: {len(path)} (efficiency: {len(path)/(len(series1)+len(series2)):.2f})")
    print(f"  Mean difference: {diff:+.3f}")


if __name__ == '__main__':
    plot_tune_comparison_dtw('Cosmic Rays', 'Bluebird')
