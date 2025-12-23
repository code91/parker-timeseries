#!/usr/bin/env python3
"""
9_autocorrelation_clustering.py
Autocorrelation analysis and tune clustering based on improvisational strategies.

Outputs:
- Autocorrelation metrics (predictability)
- Tune clusters by improvisational strategy
- Strategy characterization
"""

import subprocess
import sys

for pkg in ['pandas', 'numpy', 'matplotlib', 'seaborn', 'scikit-learn', 'scipy']:
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
from scipy.stats import pearsonr
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

INPUT_CSV = 'parker_phrases.csv'
ROBUSTNESS_CSV = 'parker_robustness_metrics.csv'
PLOTS_DIR = Path('09_autocorr_clustering_plots')
PLOTS_DIR.mkdir(exist_ok=True)

METRICS = ['mean_iv_sum', 'mean_dissonance']
LAGS = [1, 2, 3, 4, 5]


def load_data():
    """Load phrase and robustness data."""
    phrases_df = pd.read_csv(INPUT_CSV)
    robustness_df = pd.read_csv(ROBUSTNESS_CSV)
    
    print(f"Loaded {len(phrases_df)} phrases from {phrases_df['tune'].nunique()} tunes")
    print(f"Loaded robustness metrics for {len(robustness_df)} tunes")
    
    return phrases_df, robustness_df


def compute_autocorrelation(series, max_lag=5):
    """
    Compute autocorrelation for a time series up to max_lag.
    
    Returns dict: {lag: correlation_coefficient}
    """
    if len(series) < max_lag + 2:
        return {lag: np.nan for lag in range(1, max_lag + 1)}
    
    autocorr = {}
    for lag in range(1, max_lag + 1):
        if len(series) > lag:
            # Pearson correlation between series[:-lag] and series[lag:]
            try:
                corr, _ = pearsonr(series[:-lag], series[lag:])
                autocorr[lag] = corr
            except:
                autocorr[lag] = np.nan
        else:
            autocorr[lag] = np.nan
    
    return autocorr


def compute_tune_autocorrelations(phrases_df):
    """
    Compute autocorrelation metrics for each tune.
    """
    results = []
    
    print("\nComputing autocorrelations for all tunes...")
    
    for tune in phrases_df['tune'].unique():
        tune_df = phrases_df[phrases_df['tune'] == tune].sort_values('phrase_id')
        
        if len(tune_df) < 6:
            continue
        
        tune_result = {
            'tune': tune,
            'phrase_count': len(tune_df)
        }
        
        for metric in METRICS:
            values = tune_df[metric].values
            autocorr = compute_autocorrelation(values, max_lag=max(LAGS))
            
            for lag in LAGS:
                tune_result[f'{metric}_lag{lag}'] = autocorr.get(lag, np.nan)
        
        results.append(tune_result)
    
    autocorr_df = pd.DataFrame(results)
    
    print(f"Computed autocorrelations for {len(autocorr_df)} tunes")
    
    return autocorr_df


def visualize_autocorrelation_distributions(autocorr_df):
    """
    Visualize distribution of autocorrelations across corpus.
    """
    print("\nVisualizing autocorrelation distributions...")
    
    fig, axes = plt.subplots(2, len(LAGS), figsize=(18, 8))
    
    for metric_idx, metric in enumerate(METRICS):
        metric_label = 'Complexity' if metric == 'mean_iv_sum' else 'Dissonance'
        
        for lag_idx, lag in enumerate(LAGS):
            ax = axes[metric_idx, lag_idx]
            
            col_name = f'{metric}_lag{lag}'
            values = autocorr_df[col_name].dropna()
            
            ax.hist(values, bins=20, edgecolor='black', alpha=0.7, color='steelblue')
            ax.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.7)
            ax.axvline(x=values.mean(), color='green', linestyle='--', 
                      linewidth=2, alpha=0.7, label=f'Mean: {values.mean():.3f}')
            
            ax.set_xlabel(f'Autocorr (lag {lag})', fontsize=10)
            ax.set_ylabel('Frequency', fontsize=10)
            ax.set_title(f'{metric_label} - Lag {lag}', fontsize=11, fontweight='bold')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'autocorr_distributions.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/autocorr_distributions.png")

def visualize_tune_autocorrelation_profiles(autocorr_df):
    """
    Show autocorrelation profiles for strategy example tunes.
    """
    print("\nVisualizing strategy example autocorrelation profiles...")

    # Specific example tunes from the paper
    selected_tunes = [
        'Barbados',              # Strategy 1: Balanced/Moderate (Cluster 0)
        'Si Si',                 # Strategy 2: Contrasting (Cluster 1)
        'Cosmic Rays',           # Strategy 3: Exploratory (Cluster 2)
        'My Little Suede Shoes'  # Strategy 4: Volatile/Continuous (Cluster 3)
    ]

    # Filter to only tunes that exist in the data
    available_tunes = [t for t in selected_tunes if t in autocorr_df['tune'].values]

    if len(available_tunes) == 0:
        print("  WARNING: None of the example tunes found in data!")
        return

    print(f"  Plotting {len(available_tunes)} example tunes: {', '.join(available_tunes)}")

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Define colors for each strategy
    strategy_colors = {
        'Barbados': '#2ecc71',              # Green - Balanced
        'Si Si': '#e74c3c',                 # Red - Contrasting
        'Cosmic Rays': '#9b59b6',           # Purple - Exploratory
        'My Little Suede Shoes': '#f39c12'  # Orange - Volatile/Continuous (paradox)
    }

    for metric_idx, metric in enumerate(METRICS):
        ax = axes[metric_idx]
        metric_label = 'Complexity' if metric == 'mean_iv_sum' else 'Dissonance'

        for tune in available_tunes:
            tune_data = autocorr_df[autocorr_df['tune'] == tune].iloc[0]

            autocorr_values = [tune_data[f'{metric}_lag{lag}'] for lag in LAGS]

            color = strategy_colors.get(tune, '#95a5a6')  # Gray as fallback

            ax.plot(LAGS, autocorr_values, 'o-', linewidth=2.5, markersize=8,
                   color=color, label=tune, alpha=0.8)

        ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
        ax.set_xlabel('Lag (phrases)', fontsize=12)
        ax.set_ylabel('Autocorrelation', fontsize=12)
        ax.set_title(f'{metric_label}: Autocorrelation vs Lag',
                    fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(-0.6, 0.7)
        ax.set_xticks(LAGS)
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'autocorr_profiles.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/autocorr_profiles.png")


def print_autocorrelation_rankings(autocorr_df):
    """Print tunes ranked by predictability."""
    print("\n" + "="*70)
    print("AUTOCORRELATION RANKINGS (PREDICTABILITY)")
    print("="*70)
    
    for metric in METRICS:
        metric_label = 'Complexity' if metric == 'mean_iv_sum' else 'Dissonance'
        print(f"\n{metric_label} - Lag 1 (Most Predictable):")
        print(f"  {'Tune':<30s} {'Autocorr':>10s} {'Interpretation'}")
        print("  " + "-"*65)
        
        col = f'{metric}_lag1'
        sorted_df = autocorr_df.sort_values(col, ascending=False).head(10)
        
        for _, row in sorted_df.iterrows():
            tune = row['tune'][:29]
            autocorr_val = row[col]
            
            if autocorr_val > 0.5:
                interp = "Strong continuity"
            elif autocorr_val > 0.2:
                interp = "Moderate continuity"
            elif autocorr_val > -0.2:
                interp = "Low continuity"
            else:
                interp = "Contrasting"
            
            print(f"  {tune:<30s} {autocorr_val:>10.3f}  {interp}")
        
        print(f"\n{metric_label} - Lag 1 (Most Random/Contrasting):")
        print(f"  {'Tune':<30s} {'Autocorr':>10s} {'Interpretation'}")
        print("  " + "-"*65)
        
        sorted_df = autocorr_df.sort_values(col, ascending=True).head(10)
        
        for _, row in sorted_df.iterrows():
            tune = row['tune'][:29]
            autocorr_val = row[col]
            
            if autocorr_val < -0.3:
                interp = "Strong contrast"
            elif autocorr_val < 0:
                interp = "Weak contrast"
            else:
                interp = "Random walk"
            
            print(f"  {tune:<30s} {autocorr_val:>10.3f}  {interp}")


def merge_metrics_for_clustering(robustness_df, autocorr_df):
    """
    Merge robustness and autocorrelation metrics for clustering.
    """
    # Merge on tune name
    merged = robustness_df.merge(autocorr_df, on='tune', how='inner')
    
    print(f"\nMerged metrics for {len(merged)} tunes")
    
    return merged


def perform_clustering(merged_df, n_clusters=4):
    """
    Cluster tunes based on improvisational strategy.
    
    Features:
    - Complexity CV (volatility)
    - Complexity mean (density)
    - Complexity lag-1 autocorr (predictability)
    - Dissonance CV
    """
    print(f"\nPerforming k-means clustering (k={n_clusters})...")
    
    # Select features
    features = [
        'mean_iv_sum_mean',
        'mean_iv_sum_cv',
        'mean_iv_sum_lag1',
        'mean_dissonance_cv'
    ]
    
    # Filter out NaNs
    cluster_df = merged_df[['tune'] + features].dropna()
    
    print(f"Clustering {len(cluster_df)} tunes with features: {features}")
    
    # Standardize features
    scaler = StandardScaler()
    X = scaler.fit_transform(cluster_df[features])
    
    # K-means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
    cluster_df['cluster'] = kmeans.fit_predict(X)
    
    # Add cluster assignments back to merged_df
    merged_df = merged_df.merge(
        cluster_df[['tune', 'cluster']], 
        on='tune', 
        how='left'
    )
    
    # Compute cluster statistics
    print("\n" + "="*70)
    print("CLUSTER CHARACTERIZATION")
    print("="*70)
    
    for cluster_id in range(n_clusters):
        cluster_tunes = cluster_df[cluster_df['cluster'] == cluster_id]
        
        print(f"\nCluster {cluster_id} ({len(cluster_tunes)} tunes):")
        print(f"  Mean complexity: {cluster_tunes['mean_iv_sum_mean'].mean():.2f}")
        print(f"  Mean CV: {cluster_tunes['mean_iv_sum_cv'].mean():.3f}")
        print(f"  Mean autocorr lag-1: {cluster_tunes['mean_iv_sum_lag1'].mean():.3f}")
        print(f"  Mean dissonance CV: {cluster_tunes['mean_dissonance_cv'].mean():.3f}")
        
        print(f"\n  Example tunes:")
        for tune in cluster_tunes['tune'].head(5):
            print(f"    - {tune}")
    
    return merged_df, cluster_df, scaler, kmeans


def visualize_clusters(cluster_df, scaler, kmeans):
    """
    Visualize clusters in 2D using PCA.
    """
    print("\nVisualizing clusters...")
    
    features = [
        'mean_iv_sum_mean',
        'mean_iv_sum_cv',
        'mean_iv_sum_lag1',
        'mean_dissonance_cv'
    ]
    
    X = scaler.transform(cluster_df[features])
    
    # PCA for visualization
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X)
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: PCA scatter
    ax = axes[0]
    
    n_clusters = len(cluster_df['cluster'].unique())
    colors = plt.cm.tab10(np.linspace(0, 1, n_clusters))
    
    for cluster_id in range(n_clusters):
        mask = cluster_df['cluster'] == cluster_id
        ax.scatter(X_pca[mask, 0], X_pca[mask, 1], 
                  c=[colors[cluster_id]], s=100, alpha=0.7, 
                  edgecolors='black', linewidth=1,
                  label=f'Cluster {cluster_id}')
    
    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)', fontsize=12)
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)', fontsize=12)
    ax.set_title('Tune Clusters (PCA Projection)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Feature importance
    ax = axes[1]
    
    feature_labels = ['Complexity', 'Volatility (CV)', 'Predictability', 'Dissonance CV']
    pc1_weights = np.abs(pca.components_[0])
    pc2_weights = np.abs(pca.components_[1])
    
    x = np.arange(len(feature_labels))
    width = 0.35
    
    ax.bar(x - width/2, pc1_weights, width, label='PC1', color='steelblue', edgecolor='black')
    ax.bar(x + width/2, pc2_weights, width, label='PC2', color='coral', edgecolor='black')
    
    ax.set_xticks(x)
    ax.set_xticklabels(feature_labels, rotation=15, ha='right')
    ax.set_ylabel('Absolute Loading', fontsize=12)
    ax.set_title('Feature Importance in PCA', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'clusters_pca.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/clusters_pca.png")


def visualize_cluster_characteristics(merged_df):
    """
    Visualize cluster characteristics with boxplots.
    """
    print("\nVisualizing cluster characteristics...")
    
    cluster_df = merged_df.dropna(subset=['cluster'])
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    metrics = [
        ('mean_iv_sum_mean', 'Mean Complexity'),
        ('mean_iv_sum_cv', 'Volatility (CV)'),
        ('mean_iv_sum_lag1', 'Predictability (Lag-1)'),
        ('mean_dissonance_cv', 'Dissonance Volatility')
    ]
    
    for idx, (metric, label) in enumerate(metrics):
        ax = axes[idx // 2, idx % 2]
        
        # Boxplot
        cluster_df.boxplot(column=metric, by='cluster', ax=ax, patch_artist=True)
        
        ax.set_xlabel('Cluster', fontsize=11)
        ax.set_ylabel(label, fontsize=11)
        ax.set_title(f'{label} by Cluster', fontsize=12, fontweight='bold')
        ax.get_figure().suptitle('')  # Remove automatic title
        ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'cluster_characteristics.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/cluster_characteristics.png")


def assign_cluster_labels(merged_df):
    """
    Assign interpretable labels to clusters based on characteristics.
    """
    print("\nAssigning cluster strategy labels...")
    
    cluster_df = merged_df.dropna(subset=['cluster'])
    
    cluster_profiles = {}
    
    for cluster_id in cluster_df['cluster'].unique():
        cluster_data = cluster_df[cluster_df['cluster'] == cluster_id]
        
        complexity = cluster_data['mean_iv_sum_mean'].mean()
        volatility = cluster_data['mean_iv_sum_cv'].mean()
        predictability = cluster_data['mean_iv_sum_lag1'].mean()
        
        # Assign strategy label
        if volatility > 0.6 and predictability < 0.2:
            strategy = "Exploratory/Episodic"
        elif volatility > 0.6 and predictability > 0.2:
            strategy = "Volatile/Continuous"
        elif volatility < 0.4 and predictability > 0.4:
            strategy = "Stable/Predictable"
        elif complexity > 12:
            strategy = "Dense/Complex"
        else:
            strategy = "Balanced/Moderate"
        
        cluster_profiles[cluster_id] = {
            'label': strategy,
            'complexity': complexity,
            'volatility': volatility,
            'predictability': predictability
        }
    
    print("\n" + "="*70)
    print("CLUSTER STRATEGY PROFILES")
    print("="*70)
    
    for cluster_id, profile in cluster_profiles.items():
        cluster_tunes = cluster_df[cluster_df['cluster'] == cluster_id]
        
        print(f"\nCluster {cluster_id}: {profile['label']}")
        print(f"  Complexity: {profile['complexity']:.2f}")
        print(f"  Volatility: {profile['volatility']:.3f}")
        print(f"  Predictability: {profile['predictability']:.3f}")
        print(f"  Count: {len(cluster_tunes)} tunes")
        print(f"  Examples: {', '.join(cluster_tunes['tune'].head(3).tolist())}")
    
    return cluster_profiles


def main():
    print("Parker Corpus: Autocorrelation & Clustering Analysis")
    print("="*70)
    
    # Load data
    phrases_df, robustness_df = load_data()
    
    # Compute autocorrelations
    autocorr_df = compute_tune_autocorrelations(phrases_df)
    
    # Save autocorrelation metrics
    autocorr_df.to_csv('parker_autocorrelation_metrics.csv', index=False)
    print(f"\nSaved: parker_autocorrelation_metrics.csv")
    
    # Print rankings
    print_autocorrelation_rankings(autocorr_df)
    
    # Visualize autocorrelations
    visualize_autocorrelation_distributions(autocorr_df)
    visualize_tune_autocorrelation_profiles(autocorr_df)
    
    # Merge metrics for clustering
    merged_df = merge_metrics_for_clustering(robustness_df, autocorr_df)
    
    # Perform clustering
    merged_df, cluster_df, scaler, kmeans = perform_clustering(merged_df, n_clusters=4)
    
    # Save cluster assignments
    cluster_output = merged_df[['tune', 'cluster']].dropna()
    cluster_output.to_csv('parker_cluster_assignments.csv', index=False)
    print(f"\nSaved: parker_cluster_assignments.csv")
    
    # Visualize clusters
    visualize_clusters(cluster_df, scaler, kmeans)
    visualize_cluster_characteristics(merged_df)
    
    # Assign interpretable labels
    cluster_profiles = assign_cluster_labels(merged_df)
    
    # Summary
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nOutputs:")
    print(f"  - parker_autocorrelation_metrics.csv")
    print(f"  - parker_cluster_assignments.csv")
    print(f"  - {PLOTS_DIR}/autocorr_distributions.png")
    print(f"  - {PLOTS_DIR}/autocorr_profiles.png")
    print(f"  - {PLOTS_DIR}/clusters_pca.png")
    print(f"  - {PLOTS_DIR}/cluster_characteristics.png")
    
    print("\nKey Findings:")
    print("  - Autocorrelation reveals phrase-to-phrase predictability")
    print("  - High autocorr = continuous development")
    print("  - Low/negative autocorr = contrasting/episodic structure")
    print("  - Clusters reveal distinct improvisational strategies")
    
    print("\nNext step: Granger causality (does complexity predict dissonance?)")


if __name__ == '__main__':
    main()
