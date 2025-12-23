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
- Per-tune Granger test results
- Cluster-level causality patterns
- Visualization of causal strength
"""

import subprocess
import sys

for pkg in ['pandas', 'numpy', 'matplotlib', 'seaborn', 'statsmodels']:
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
    
    # Ensure stationarity by differencing if needed
    # (For now, use raw data - can add differencing if needed)
    
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
        median_pval = valid[pval_col].median()
        
        print(f"  Lag {lag}:")
        print(f"    Significant: {significant}/{len(valid)} ({pct_significant:.1f}%)")
        print(f"    Mean F-stat: {mean_fstat:.3f}")
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

    # FILTER OUT cXbwc
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
    analyze_by_cluster(results_df)
    identify_top_gravity_tunes(results_df)
    
    # Visualizations
    print("\n" + "="*70)
    print("GENERATING VISUALIZATIONS")
    print("="*70)
    
    visualize_causality_heatmap(results_df)
    visualize_causality_by_cluster(results_df)
    visualize_significance_bars(results_df)
    
    # Summary
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nOutputs:")
    print(f"  - parker_granger_results.csv")
    print(f"  - {PLOTS_DIR}/causality_heatmap.png")
    print(f"  - {PLOTS_DIR}/causality_by_cluster.png")
    print(f"  - {PLOTS_DIR}/significance_by_lag.png")
    
    print("\nInterpretation Guide:")
    print("  - F-statistic: Strength of causal relationship")
    print("  - p-value < 0.05: Significant causality")
    print("  - >5% significant = real effect (vs 5% expected by chance)")
    print("  - Compare clusters to see if strategies differ")
    
    print("\nKey Questions Answered:")
    print("  1. Does complexity predict dissonance? (tension creation)")
    print("  2. Does dissonance predict complexity? (response)")
    print("  3. Are effects immediate (lag-1) or delayed (lag-2/3)?")
    print("  4. Do clusters show different causal patterns?")


if __name__ == '__main__':
    main()
