"""
Parker Corpus Network Analysis
==============================

Process all MusicXML files from the Parker Omnibook corpus and build
an aggregated network of intervallic transitions.

Corpus License: CC BY-NC-SA 2.0
Citation: Déguernel, Vincent, Assayag. "Using Multidimensional Sequences 
          for Improvisation in the OMax Paradigm", SMC 2016.
Original copyrights: Atlantic Music Corp.

"""

import os
import json
import csv
from pathlib import Path
from collections import defaultdict, Counter
from musicxml_to_pcs import PCSExtractor
from music21 import converter
import networkx as nx


def load_tune_titles(csv_path='tune_titles.csv'):
    """Load ID-to-title mapping from CSV."""
    titles = {}
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                titles[row['id']] = row['title']
        print(f"Loaded {len(titles)} tune titles from {csv_path}\n")
    except FileNotFoundError:
        print(f"Warning: {csv_path} not found. Using file IDs as titles.\n")
    return titles


def detect_key(filepath):
    """
    Detect the key of a MusicXML file using Krumhansl-Schmuckler algorithm.

    Returns:
        Tuple of (key_root_pc, mode, confidence)
    """
    score = converter.parse(filepath)
    key = score.analyze('key')
    return key.tonic.pitchClass, key.mode, key.correlationCoefficient


def get_roman_numeral(chord_root, chord_kind, key_root):
    """Convert chord to Roman numeral based on key."""
    degree = (chord_root - key_root) % 12

    degree_map = {
        0: 'I', 1: 'bII', 2: 'II', 3: 'bIII', 4: 'III', 5: 'IV',
        6: '#IV', 7: 'V', 8: 'bVI', 9: 'VI', 10: 'bVII', 11: 'VII'
    }

    roman = degree_map.get(degree, '?')

    if chord_kind in ['min', 'min7']:
        roman += '-'
    elif chord_kind in ['dom', 'dom7']:
        roman += '7'
    elif chord_kind in ['dim', 'dim7']:
        roman += '°'
    elif chord_kind in ['hdim']:
        roman += 'ø'
    elif chord_kind in ['maj7']:
        roman += 'Δ'

    return roman


def get_relative_pcs(pitch_classes, chord_root):
    """Convert absolute pitch classes to relative (chord root = 0)."""
    return sorted((pc - chord_root) % 12 for pc in pitch_classes)


def process_corpus(omnibook_dir, titles_map=None, min_cardinality=3):
    """
    Process all MusicXML files in the corpus.

    Args:
        omnibook_dir: Path to folder containing MusicXML files
        titles_map: Dict mapping file IDs to tune titles
        min_cardinality: Minimum pitch classes per segment

    Returns:
        Tuple of (NetworkX DiGraph, list of tune info dicts, list of all segments)
    """
    if titles_map is None:
        titles_map = {}

    omnibook_path = Path(omnibook_dir)
    xml_files = sorted(omnibook_path.glob('*.xml'))

    print(f"Found {len(xml_files)} MusicXML files\n")

    # Aggregated data
    function_associations = defaultdict(Counter)
    chord_associations = defaultdict(Counter)
    relative_pcs_by_function = defaultdict(lambda: defaultdict(list))
    edge_counts = Counter()

    # Track per-tune info
    tune_info = []
    total_segments = 0

    # NEW: Sequential data for time series
    all_segments_sequential = []

    pc_to_name = {0: 'C', 1: 'Db', 2: 'D', 3: 'Eb', 4: 'E', 5: 'F',
                  6: 'F#', 7: 'G', 8: 'Ab', 9: 'A', 10: 'Bb', 11: 'B'}

    for xml_file in xml_files:
        file_id = xml_file.stem  # e.g., "2RfYc"
        print(f"Processing: {file_id}...", end=" ")

        try:
            # Parse score to get key
            score = converter.parse(str(xml_file))

            # Get title from mapping, fall back to file ID
            tune_title = titles_map.get(file_id, file_id)

            # Detect key
            key = score.analyze('key')
            key_root, mode, confidence = key.tonic.pitchClass, key.mode, key.correlationCoefficient
            key_name = f"{pc_to_name[key_root]} {mode}"

            # Extract segments
            extractor = PCSExtractor(str(xml_file))
            segments = extractor.extract(min_cardinality=min_cardinality)

            print(f"{tune_title} | {key_name} ({confidence:.0%}), {len(segments)} segments")

            tune_info.append({
                'id': file_id,
                'title': tune_title,
                'key': key_name,
                'key_root': key_root,
                'confidence': confidence,
                'segments': len(segments)
            })

            # Process segments
            for idx, seg in enumerate(segments):
                iv_str = seg.interval_vector_string
                iv = seg.interval_vector  # [ic1, ic2, ic3, ic4, ic5, ic6]
                chord = seg.chord_symbol
                chord_kind = seg.chord_kind
                roman = get_roman_numeral(seg.chord_root, chord_kind, key_root)
                relative_pcs = get_relative_pcs(seg.pitch_classes, seg.chord_root)

                # Aggregated associations (for network)
                function_associations[iv_str][roman] += 1
                chord_associations[iv_str][chord] += 1
                relative_pcs_by_function[iv_str][roman].append(relative_pcs)

                # NEW: Sequential record for time series
                all_segments_sequential.append({
                    'id': file_id,
                    'tune': tune_title,
                    'segment_idx': idx,
                    'measure': seg.measure,
                    'beat': seg.beat,
                    'chord_symbol': chord,
                    'chord_function': roman,
                    'key': key_name,
                    'iv': iv_str,
                    'ic1': iv[0],
                    'ic2': iv[1],
                    'ic3': iv[2],
                    'ic4': iv[3],
                    'ic5': iv[4],
                    'ic6': iv[5],
                    'iv_sum': sum(iv),
                    'forte_class': seg.forte_class,
                    'cardinality': len(seg.pitch_classes),
                    'note_count': seg.note_count,
                    'pitch_classes': str(seg.pitch_classes),
                    'relative_pcs': str(relative_pcs)
                })

            # Collect edges (within this tune only)
            for i in range(len(segments) - 1):
                source = segments[i].interval_vector_string
                target = segments[i + 1].interval_vector_string
                edge_counts[(source, target)] += 1

            total_segments += len(segments)

        except Exception as e:
            print(f"ERROR: {e}")
            tune_info.append({
                'id': file_id,
                'title': file_id,
                'error': str(e)
            })

    print(f"\n{'='*60}")
    print(f"Total: {len(tune_info)} tunes, {total_segments} segments")
    print(f"{'='*60}")

    # Build the graph
    G = nx.DiGraph()

    all_ivs = set(function_associations.keys()) | set(chord_associations.keys())
    for iv_str in all_ivs:
        functions = function_associations[iv_str]
        chords = chord_associations[iv_str]

        regeneration_data = {}
        for roman, pcs_list in relative_pcs_by_function[iv_str].items():
            pcs_counts = Counter(tuple(pcs) for pcs in pcs_list)
            regeneration_data[roman] = {
                str(list(pcs)): count for pcs, count in pcs_counts.items()
            }

        G.add_node(
            iv_str,
            chord_symbols=dict(chords),
            chord_functions=dict(functions),
            relative_pcs_by_function=regeneration_data,
            total_occurrences=sum(chords.values()),
            primary_chord=max(chords, key=chords.get) if chords else None,
            primary_function=max(functions, key=functions.get) if functions else None
        )

    for (source, target), weight in edge_counts.items():
        G.add_edge(source, target, weight=weight)

    return G, tune_info, all_segments_sequential


def export_sequential_csv(segments, filepath):
    """
    Export all segments in sequential order for time series analysis.

    Each row is a single harmonic segment with full IV breakdown.
    """
    if not segments:
        print("No segments to export")
        return

    fieldnames = [
        'id', 'tune', 'segment_idx', 'measure', 'beat',
        'chord_symbol', 'chord_function', 'key',
        'iv', 'ic1', 'ic2', 'ic3', 'ic4', 'ic5', 'ic6', 'iv_sum',
        'forte_class', 'cardinality', 'note_count',
        'pitch_classes', 'relative_pcs'
    ]

    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(segments)

    print(f"Exported {len(segments)} sequential segments to {filepath}")


def export_network(G, tune_info, filepath):
    """Export network to JSON with metadata."""
    data = {
        'metadata': {
            'corpus': 'Charlie Parker Omnibook',
            'license': 'CC BY-NC-SA 2.0',
            'citation': 'Déguernel, Vincent, Assayag. SMC 2016.',
            'tunes_processed': len([t for t in tune_info if 'error' not in t]),
            'total_segments': sum(t.get('segments', 0) for t in tune_info)
        },
        'tunes': tune_info,
        'nodes': [],
        'edges': []
    }

    for node, attrs in G.nodes(data=True):
        data['nodes'].append({
            'id': node,
            **attrs
        })

    for source, target, attrs in G.edges(data=True):
        data['edges'].append({
            'source': source,
            'target': target,
            **attrs
        })

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Exported network to {filepath}")


def export_for_cosmograph(G, base_filepath):
    """
    Export network as two CSVs for Cosmograph visualization.

    Creates:
      - {base}_nodes.csv: id, size, label, cluster (primary function)
      - {base}_edges.csv: source, target, weight
    """
    # Nodes CSV
    nodes_file = f"{base_filepath}_nodes.csv"
    with open(nodes_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'size', 'label', 'cluster'])

        for node, attrs in G.nodes(data=True):
            size = attrs.get('total_occurrences', 1)
            label = node  # interval vector as label
            cluster = attrs.get('primary_function', 'unknown')
            writer.writerow([node, size, label, cluster])

    print(f"Exported nodes to {nodes_file}")

    # Edges CSV
    edges_file = f"{base_filepath}_edges.csv"
    with open(edges_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['source', 'target', 'weight'])

        for source, target, attrs in G.edges(data=True):
            weight = attrs.get('weight', 1)
            writer.writerow([source, target, weight])

    print(f"Exported edges to {edges_file}")


def analyze_network(G):
    """Print network statistics."""
    print(f"\n{'='*60}")
    print("AGGREGATED NETWORK STATISTICS")
    print(f"{'='*60}")

    print(f"\nNodes (unique interval vectors): {G.number_of_nodes()}")
    print(f"Edges (unique transitions): {G.number_of_edges()}")
    print(f"Total transitions: {sum(d['weight'] for _, _, d in G.edges(data=True))}")

    print(f"\nTop 15 nodes by total occurrences:")
    nodes_by_occ = sorted(G.nodes(data=True), key=lambda x: -x[1].get('total_occurrences', 0))
    for node, data in nodes_by_occ[:15]:
        funcs = data.get('chord_functions', {})
        primary = data.get('primary_function', '?')
        print(f"  {node}: {data.get('total_occurrences', 0):4d}x | primary: {primary:5s} | {dict(funcs)}")

    print(f"\nTop 15 most frequent transitions:")
    edges = [(u, v, d['weight']) for u, v, d in G.edges(data=True)]
    for source, target, weight in sorted(edges, key=lambda x: -x[2])[:15]:
        src_func = G.nodes[source].get('primary_function', '?')
        tgt_func = G.nodes[target].get('primary_function', '?')
        print(f"  {source} ({src_func:5s}) -> {target} ({tgt_func:5s}): {weight}x")


def analyze_iv_distribution(segments):
    """Analyze interval class distribution across corpus for PCA planning."""
    import numpy as np

    print(f"\n{'='*60}")
    print("INTERVAL CLASS DISTRIBUTION (for PCA planning)")
    print(f"{'='*60}")

    # Extract IV matrix
    iv_matrix = np.array([
        [s['ic1'], s['ic2'], s['ic3'], s['ic4'], s['ic5'], s['ic6']]
        for s in segments
    ])

    print(f"\nTotal segments: {len(iv_matrix)}")
    print(f"\nPer interval class statistics:")
    print(f"{'IC':<6} {'Mean':>8} {'Std':>8} {'Min':>6} {'Max':>6} {'Zero%':>8}")
    print("-" * 50)

    ic_names = ['ic1 (m2)', 'ic2 (M2)', 'ic3 (m3)', 'ic4 (M3)', 'ic5 (P4)', 'ic6 (TT)']
    for i, name in enumerate(ic_names):
        col = iv_matrix[:, i]
        zero_pct = (col == 0).sum() / len(col) * 100
        print(f"{name:<10} {col.mean():>6.2f} {col.std():>8.2f} {col.min():>6} {col.max():>6} {zero_pct:>7.1f}%")

    print(f"\nIV sum statistics:")
    iv_sums = iv_matrix.sum(axis=1)
    print(f"  Mean: {iv_sums.mean():.2f}")
    print(f"  Std:  {iv_sums.std():.2f}")
    print(f"  Min:  {iv_sums.min()}")
    print(f"  Max:  {iv_sums.max()}")

    # Correlation matrix
    print(f"\nCorrelation matrix between interval classes:")
    corr = np.corrcoef(iv_matrix.T)
    print(f"{'':>10}", end="")
    for i in range(6):
        print(f"{'ic'+str(i+1):>8}", end="")
    print()
    for i in range(6):
        print(f"{'ic'+str(i+1):>10}", end="")
        for j in range(6):
            print(f"{corr[i,j]:>8.2f}", end="")
        print()

    return iv_matrix


def main():
    # Load tune titles
    titles_map = load_tune_titles('tune_titles.csv')

    # Process all tunes
    omnibook_dir = 'xml'  # Folder containing MusicXML files

    G, tune_info, all_segments = process_corpus(omnibook_dir, titles_map, min_cardinality=3)

    # Analyze
    analyze_network(G)

    # Analyze IV distribution
    analyze_iv_distribution(all_segments)

    # Export JSON (full data)
    export_network(G, tune_info, 'parker_corpus_network.json')

    # Export for Cosmograph
    export_for_cosmograph(G, 'parker_corpus')

    # NEW: Export sequential data for time series
    export_sequential_csv(all_segments, 'parker_sequential.csv')

    return G, tune_info, all_segments


if __name__ == '__main__':
    G, tune_info, all_segments = main()
