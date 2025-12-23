#!/usr/bin/env python3
"""
7_phrase_detection.py
Detect phrase boundaries using rests from MusicXML transcriptions.

Outputs:
- Rest distribution analysis
- Phrase length distributions
- Visualization of phrase boundaries
- Phrase-segmented dataset
- Musical phrase diagrams
"""

import subprocess
import sys

for pkg in ['pandas', 'numpy', 'matplotlib', 'lxml', 'music21']:
    try:
        __import__(pkg)
    except ImportError:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from lxml import etree
from music21 import stream, note, meter, tempo, clef, metadata
import warnings
warnings.filterwarnings('ignore')

INPUT_CSV = 'parker_timeseries.csv'
XML_DIR = 'xml'
PLOTS_DIR = Path('07_phrase_plots')
PLOTS_DIR.mkdir(exist_ok=True)


def load_data(path: str) -> pd.DataFrame:
    """Load timeseries data."""
    df = pd.read_csv(path)
    df = df.dropna(subset=['timestamp_ms'])
    print(f"Loaded {len(df)} segments from {len(df['tune'].unique())} tunes")
    return df


def parse_rests_from_xml(xml_path: str) -> list:
    """
    Extract all rests from a MusicXML file with their positions.

    Returns list of dicts: {measure, beat, duration_divisions, type}
    """
    tree = etree.parse(xml_path)
    root = tree.getroot()

    # Get divisions (ticks per quarter note)
    divisions = int(root.find('.//divisions').text)

    rests = []
    current_measure = 1
    current_beat_position = 0  # in divisions

    # Iterate through all parts and measures
    for part in root.findall('.//part'):
        current_measure = 1

        for measure in part.findall('.//measure'):
            measure_number = int(measure.get('number', current_measure))
            current_beat_position = 0

            # Process all note/rest elements in order
            for element in measure:
                if element.tag == 'attributes':
                    # Update divisions if it changes
                    div_elem = element.find('.//divisions')
                    if div_elem is not None:
                        divisions = int(div_elem.text)

                elif element.tag == 'note':
                    duration = int(element.find('duration').text)

                    # Check if it's a rest
                    if element.find('rest') is not None:
                        # Calculate beat position (1-indexed, fractional)
                        beat = (current_beat_position / divisions) + 1

                        # Get rest type (eighth, quarter, etc.)
                        rest_type = element.find('type')
                        rest_type_str = rest_type.text if rest_type is not None else 'unknown'

                        rests.append({
                            'measure': measure_number,
                            'beat': beat,
                            'duration_divisions': duration,
                            'duration_quarters': duration / divisions,
                            'type': rest_type_str
                        })

                    # Advance position
                    current_beat_position += duration

            current_measure = measure_number + 1

    return rests


def extract_all_rests(xml_dir: str, tune_titles: dict = None) -> pd.DataFrame:
    """Extract rests from all MusicXML files."""
    xml_path = Path(xml_dir)
    xml_files = sorted(xml_path.glob('*.xml'))

    all_rests = []

    print("\nExtracting rests from MusicXML files...")
    for xml_file in xml_files:
        tune_id = xml_file.stem

        try:
            rests = parse_rests_from_xml(str(xml_file))

            for rest in rests:
                rest['id'] = tune_id
                all_rests.append(rest)

            print(f"  {tune_id}: {len(rests)} rests")

        except Exception as e:
            print(f"  {tune_id}: ERROR - {e}")

    rests_df = pd.DataFrame(all_rests)
    print(f"\nTotal rests extracted: {len(rests_df)} from {len(xml_files)} files")

    return rests_df


def analyze_rest_distribution(rests_df: pd.DataFrame):
    """Analyze rest duration distribution."""
    print("\n" + "="*70)
    print("REST DISTRIBUTION ANALYSIS")
    print("="*70)

    print(f"\nTotal rests: {len(rests_df)}")
    print(f"Mean duration: {rests_df['duration_quarters'].mean():.2f} quarter notes")
    print(f"Median duration: {rests_df['duration_quarters'].median():.2f} quarter notes")

    # By type
    print("\nRest types:")
    type_counts = rests_df['type'].value_counts()
    for rest_type, count in type_counts.items():
        pct = count / len(rests_df) * 100
        bar = '█' * int(pct / 2)
        print(f"  {rest_type:12s}: {count:5d} ({pct:5.1f}%) {bar}")

    # Visualize
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Duration distribution
    ax = axes[0]
    ax.hist(rests_df['duration_quarters'], bins=30, edgecolor='black', alpha=0.7)
    ax.set_xlabel('Rest Duration (quarter notes)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Distribution of Rest Durations', fontsize=14)
    ax.axvline(x=rests_df['duration_quarters'].median(), color='red',
               linestyle='--', linewidth=2,
               label=f"Median: {rests_df['duration_quarters'].median():.2f}")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Type counts
    ax = axes[1]
    type_counts_sorted = type_counts.sort_values(ascending=False)
    ax.bar(range(len(type_counts_sorted)), type_counts_sorted.values,
           color='steelblue', edgecolor='black')
    ax.set_xticks(range(len(type_counts_sorted)))
    ax.set_xticklabels(type_counts_sorted.index, rotation=45, ha='right')
    ax.set_ylabel('Count', fontsize=12)
    ax.set_title('Rest Types Distribution', fontsize=14)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'rest_distribution.png', dpi=150)
    plt.close()
    print(f"\n  Saved: {PLOTS_DIR}/rest_distribution.png")


def match_rests_to_segments(df: pd.DataFrame, rests_df: pd.DataFrame,
                            min_duration_quarters: float = 0.25) -> pd.DataFrame:
    """
    Match rests to segments and mark phrase boundaries.
    AGGRESSIVE: Every rest creates a boundary, even if position match is fuzzy.
    """
    print("\n" + "="*70)
    print("MATCHING RESTS TO SEGMENTS")
    print("="*70)

    print(f"\nFiltering rests >= {min_duration_quarters} quarter notes...")
    rests_filtered = rests_df[rests_df['duration_quarters'] >= min_duration_quarters].copy()
    print(f"Using {len(rests_filtered)} rests (filtered from {len(rests_df)})")

    # Add phrase boundary markers to segments
    df = df.copy()
    df['phrase_boundary_after'] = False
    df['rest_duration_after'] = 0.0

    matched_count = 0
    unmatched_rests = 0

    for _, rest in rests_filtered.iterrows():
        # Strategy: Find the segment closest to this rest

        # 1. Try exact match (measure + beat within tolerance)
        mask = (
            (df['id'] == rest['id']) &
            (df['measure'] == rest['measure']) &
            (df['beat'] <= rest['beat']) &
            (df['beat'] >= rest['beat'] - 4)  # Within 4 beats
        )
        matching_segments = df[mask]

        # 2. If no match, try just measure (get last segment in that measure)
        if len(matching_segments) == 0:
            mask = (
                (df['id'] == rest['id']) &
                (df['measure'] == rest['measure'])
            )
            matching_segments = df[mask]

        # 3. If still no match, get last segment BEFORE this measure
        if len(matching_segments) == 0:
            mask = (
                (df['id'] == rest['id']) &
                (df['measure'] < rest['measure'])
            )
            matching_segments = df[mask]

        # 4. If STILL no match, get ANY segment from this tune
        if len(matching_segments) == 0:
            mask = (df['id'] == rest['id'])
            matching_segments = df[mask]

        if len(matching_segments) > 0:
            # Get the last segment from matches
            segment_idx = matching_segments.index[-1]

            # Only mark if not already marked (avoid duplicates)
            if not df.loc[segment_idx, 'phrase_boundary_after']:
                df.loc[segment_idx, 'phrase_boundary_after'] = True
                df.loc[segment_idx, 'rest_duration_after'] = rest['duration_quarters']
                matched_count += 1
        else:
            # This should never happen with strategy 4
            unmatched_rests += 1

    print(f"\nMatched {matched_count} rests to segments")
    if unmatched_rests > 0:
        print(f"Unmatched rests: {unmatched_rests} (likely in sections with no note data)")

    boundary_count = df['phrase_boundary_after'].sum()
    print(f"Total phrase boundaries marked: {boundary_count}")

    return df


def create_phrases(df: pd.DataFrame) -> pd.DataFrame:
    """Group segments into phrases based on rest boundaries."""
    print("\n" + "="*70)
    print("CREATING PHRASE DATASET")
    print("="*70)

    phrases = []
    phrase_id = 0

    for tune in df['tune'].unique():
        tune_df = df[df['tune'] == tune].sort_values('timestamp_ms').reset_index(drop=True)

        phrase_start_idx = 0

        for i in range(len(tune_df)):
            # Check if this segment has a phrase boundary after it
            if tune_df.loc[i, 'phrase_boundary_after'] or i == len(tune_df) - 1:
                # End of phrase
                phrase_segments = tune_df.iloc[phrase_start_idx:i+1]

                phrases.append({
                    'phrase_id': phrase_id,
                    'tune': tune,
                    'tune_id': tune_df.iloc[0]['id'],
                    'start_segment_idx': phrase_start_idx,
                    'end_segment_idx': i,
                    'segment_count': len(phrase_segments),
                    'start_measure': phrase_segments.iloc[0]['measure'],
                    'end_measure': phrase_segments.iloc[-1]['measure'],
                    'start_timestamp_ms': phrase_segments.iloc[0]['timestamp_ms'],
                    'end_timestamp_ms': phrase_segments.iloc[-1]['timestamp_ms'],
                    'duration_ms': phrase_segments.iloc[-1]['timestamp_ms'] -
                                  phrase_segments.iloc[0]['timestamp_ms'],
                    'mean_iv_sum': phrase_segments['iv_sum'].mean(),
                    'max_iv_sum': phrase_segments['iv_sum'].max(),
                    'min_iv_sum': phrase_segments['iv_sum'].min(),
                    'std_iv_sum': phrase_segments['iv_sum'].std(),
                    'mean_dissonance': phrase_segments['dissonance'].mean(),
                    'std_dissonance': phrase_segments['dissonance'].std(),
                    'mean_iv_distance': phrase_segments['iv_distance'].mean(),
                    'rest_duration_quarters': tune_df.loc[i, 'rest_duration_after'] if i < len(tune_df) - 1 else 0
                })

                phrase_id += 1
                phrase_start_idx = i + 1

    phrases_df = pd.DataFrame(phrases)

    print(f"\nCreated {len(phrases_df)} phrases across {df['tune'].nunique()} tunes")
    print(f"\nPhrase statistics:")
    print(f"  Mean segments per phrase: {phrases_df['segment_count'].mean():.1f}")
    print(f"  Median segments per phrase: {phrases_df['segment_count'].median():.1f}")
    print(f"  Mean duration: {phrases_df['duration_ms'].mean()/1000:.1f}s")
    print(f"  Median duration: {phrases_df['duration_ms'].median()/1000:.1f}s")
    print(f"  Shortest phrase: {phrases_df['segment_count'].min()} segments")
    print(f"  Longest phrase: {phrases_df['segment_count'].max()} segments")

    # Segment distribution
    print(f"\nPhrase length distribution:")
    length_bins = [1, 2, 3, 4, 5, 6, 8, 10, 15, 100]
    for i in range(len(length_bins) - 1):
        count = len(phrases_df[
            (phrases_df['segment_count'] >= length_bins[i]) &
            (phrases_df['segment_count'] < length_bins[i+1])
        ])
        pct = count / len(phrases_df) * 100
        label = f"{length_bins[i]}-{length_bins[i+1]-1}" if length_bins[i+1] < 100 else f"{length_bins[i]}+"
        bar = '█' * int(pct / 2)
        print(f"  {label:8s} segments: {count:4d} ({pct:5.1f}%) {bar}")

    return phrases_df


def visualize_phrases(df: pd.DataFrame, phrases_df: pd.DataFrame, tune_name: str):
    """Visualize phrases for one tune."""
    print(f"\nVisualizing phrases for: {tune_name}")

    tune_df = df[df['tune'] == tune_name].sort_values('timestamp_ms')
    tune_phrases = phrases_df[phrases_df['tune'] == tune_name]

    if len(tune_df) == 0:
        print(f"  Tune not found: {tune_name}")
        return

    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

    # Convert to seconds
    t = tune_df['timestamp_ms'].values / 1000

    # Plot 1: Complexity with phrase boundaries
    ax = axes[0]
    ax.plot(t, tune_df['iv_sum'], 'o-', linewidth=1.5, markersize=4,
            color='steelblue', alpha=0.7, label='IV Sum')

    # Mark phrase boundaries
    for _, phrase in tune_phrases.iterrows():
        boundary_time = phrase['end_timestamp_ms'] / 1000
        rest_dur = phrase['rest_duration_quarters']
        if rest_dur > 0:  # Don't mark after last phrase
            ax.axvline(x=boundary_time, color='red', linestyle='--',
                      alpha=0.6, linewidth=1.5)

    ax.set_ylabel('IV Sum (Complexity)', fontsize=12)
    ax.set_title(f'{tune_name}: Phrase Boundaries from XML Rests ({len(tune_phrases)} phrases)',
                fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # Plot 2: Phrase-level aggregated complexity
    ax = axes[1]

    phrase_times = []
    phrase_means = []
    phrase_stds = []

    for _, phrase in tune_phrases.iterrows():
        # Use midpoint of phrase for x-position
        phrase_time = (phrase['start_timestamp_ms'] + phrase['end_timestamp_ms']) / 2 / 1000
        phrase_times.append(phrase_time)
        phrase_means.append(phrase['mean_iv_sum'])
        phrase_stds.append(phrase['std_iv_sum'])

    phrase_times = np.array(phrase_times)
    phrase_means = np.array(phrase_means)
    phrase_stds = np.array(phrase_stds)

    # Bar plot with error bars
    ax.bar(phrase_times, phrase_means, width=0.5, alpha=0.7,
           color='darkorange', edgecolor='black', yerr=phrase_stds,
           capsize=3, label='Mean ± Std')

    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Mean IV Sum per Phrase', fontsize=12)
    ax.set_title('Phrase-Level Complexity', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    filename = f"{tune_name.replace(' ', '_')}_phrases.png"
    plt.savefig(PLOTS_DIR / filename, dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/{filename}")

def annotate_score_with_phrases_from_rests(xml_path: str, min_duration_quarters: float = 0.5):
    """
    Annotate score by parsing rests directly from XML.
    Marks every rest that meets duration threshold.
    """
    from lxml import etree

    print(f"\nAnnotating score with phrase boundaries from rests...")

    tune_name = Path(xml_path).stem

    # Load XML
    tree = etree.parse(xml_path)
    root = tree.getroot()

    # Get divisions
    divisions = int(root.find('.//divisions').text)
    print(f"  Divisions: {divisions}")

    boundaries_added = 0

    # Iterate through all parts
    for part in root.findall('.//part'):
        measures = part.findall('.//measure')

        for measure_idx, measure in enumerate(measures):
            measure_number = int(measure.get('number', measure_idx + 1))

            # Get all elements in this measure
            elements = list(measure)

            # Collect insertions for this measure
            insertions = []

            for i, element in enumerate(elements):
                if element.tag == 'note' and element.find('rest') is not None:
                    duration = int(element.find('duration').text)
                    duration_quarters = duration / divisions

                    if duration_quarters >= min_duration_quarters:
                        # Look for previous note in THIS measure first
                        previous_note_elem = None
                        previous_note_measure = measure

                        for j in range(i-1, -1, -1):
                            if elements[j].tag == 'note' and elements[j].find('rest') is None:
                                previous_note_elem = elements[j]
                                break

                        # If no previous note in this measure, look in PREVIOUS measure
                        if previous_note_elem is None and measure_idx > 0:
                            prev_measure = measures[measure_idx - 1]
                            prev_elements = list(prev_measure)

                            # Find last note (not rest) in previous measure
                            for elem in reversed(prev_elements):
                                if elem.tag == 'note' and elem.find('rest') is None:
                                    previous_note_elem = elem
                                    previous_note_measure = prev_measure
                                    break

                        if previous_note_elem is not None:
                            # Create boundary marker
                            direction = etree.Element('direction')
                            direction.set('placement', 'above')
                            direction_type = etree.SubElement(direction, 'direction-type')
                            words = etree.SubElement(direction_type, 'words')
                            words.text = "||"
                            words.set('font-size', '16')
                            words.set('font-weight', 'bold')
                            words.set('color', '#FF0000')

                            # Store for insertion
                            if previous_note_measure == measure:
                                # Same measure - insert after the note
                                note_idx = list(measure).index(previous_note_elem)
                                insertions.append((note_idx, direction))
                            else:
                                # Previous measure - insert at end of that measure
                                prev_note_idx = list(previous_note_measure).index(previous_note_elem)
                                prev_measure_insertions = [(prev_note_idx, direction)]
                                # Apply immediately to previous measure
                                for idx, direc in sorted(prev_measure_insertions, key=lambda x: x[0], reverse=True):
                                    previous_note_measure.insert(idx + 1, direc)
                                    boundaries_added += 1

                            print(f"    Boundary at measure {measure_number} (rest: {duration_quarters:.2f}q)")

            # Apply insertions for current measure
            for note_idx, direction in sorted(insertions, key=lambda x: x[0], reverse=True):
                measure.insert(note_idx + 1, direction)
                boundaries_added += 1

    print(f"  Total boundaries added: {boundaries_added}")

    # Save
    output_path = PLOTS_DIR / f"{tune_name}_annotated.xml"
    tree.write(str(output_path), encoding='utf-8', xml_declaration=True, pretty_print=True)
    print(f"  Saved: {output_path}")
    print(f"  Open in MuseScore to view")


def create_phrase_diagram(phrases_df: pd.DataFrame, tune_name: str):
    """
    Create simplified musical notation showing phrase structure.
    """
    print(f"\nCreating phrase diagram for: {tune_name}")

    tune_phrases = phrases_df[phrases_df['tune'] == tune_name].sort_values('phrase_id')

    if len(tune_phrases) == 0:
        print(f"  No phrases found for {tune_name}")
        return

    # Create score
    s = stream.Score()
    s.metadata = metadata.Metadata()
    s.metadata.title = f"{tune_name} - Phrase Structure"
    s.metadata.composer = "Charlie Parker"

    part = stream.Part()

    # Add 4/4 time signature and tempo
    part.append(meter.TimeSignature('4/4'))
    part.append(clef.TrebleClef())
    part.append(tempo.MetronomeMark(number=120))

    # Map complexity to pitch range (C4 to C6)
    min_complexity = tune_phrases['mean_iv_sum'].min()
    max_complexity = tune_phrases['mean_iv_sum'].max()
    complexity_range = max_complexity - min_complexity if max_complexity > min_complexity else 1

    for i, (_, phrase) in enumerate(tune_phrases.iterrows(), 1):
        # Calculate pitch based on complexity
        normalized_complexity = (phrase['mean_iv_sum'] - min_complexity) / complexity_range
        pitch_midi = int(60 + normalized_complexity * 24)
        pitch_midi = max(48, min(84, pitch_midi))

        # Duration in quarter notes
        duration_quarters = min(phrase['segment_count'], 8)

        # Create note
        n = note.Note(pitch_midi, quarterLength=duration_quarters)
        n.lyric = f"P{i}"

        part.append(n)

    s.append(part)

    # Export as PNG
    output_path = PLOTS_DIR / f"{tune_name.replace(' ', '_')}_phrase_diagram.png"

    try:
        s.write('musicxml.png', fp=str(output_path))
        print(f"  Saved phrase diagram: {output_path}")
    except Exception as e:
        print(f"  Could not create diagram: {e}")


def create_summary_visualization(phrases_df: pd.DataFrame):
    """Create summary visualizations of phrase characteristics."""
    print("\nCreating summary visualizations...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Phrase length distribution
    ax = axes[0, 0]
    ax.hist(phrases_df['segment_count'], bins=30, edgecolor='black', alpha=0.7, color='steelblue')
    ax.axvline(x=phrases_df['segment_count'].mean(), color='red', linestyle='--',
               linewidth=2, label=f"Mean: {phrases_df['segment_count'].mean():.1f}")
    ax.axvline(x=phrases_df['segment_count'].median(), color='orange', linestyle='--',
               linewidth=2, label=f"Median: {phrases_df['segment_count'].median():.1f}")
    ax.set_xlabel('Segments per Phrase', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Phrase Length Distribution', fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Phrase duration distribution
    ax = axes[0, 1]
    durations_sec = phrases_df['duration_ms'] / 1000
    ax.hist(durations_sec, bins=30, edgecolor='black', alpha=0.7, color='green')
    ax.axvline(x=durations_sec.mean(), color='red', linestyle='--',
               linewidth=2, label=f"Mean: {durations_sec.mean():.1f}s")
    ax.axvline(x=durations_sec.median(), color='orange', linestyle='--',
               linewidth=2, label=f"Median: {durations_sec.median():.1f}s")
    ax.set_xlabel('Phrase Duration (seconds)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Phrase Duration Distribution', fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Mean complexity per phrase
    ax = axes[1, 0]
    ax.hist(phrases_df['mean_iv_sum'], bins=30, edgecolor='black', alpha=0.7, color='darkorange')
    ax.axvline(x=phrases_df['mean_iv_sum'].mean(), color='red', linestyle='--',
               linewidth=2, label=f"Mean: {phrases_df['mean_iv_sum'].mean():.1f}")
    ax.set_xlabel('Mean IV Sum per Phrase', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Phrase Complexity Distribution', fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Phrase length vs complexity
    ax = axes[1, 1]
    scatter = ax.scatter(phrases_df['segment_count'], phrases_df['mean_iv_sum'],
                        c=phrases_df['duration_ms']/1000, cmap='viridis',
                        alpha=0.5, s=30, edgecolors='black', linewidth=0.5)
    ax.set_xlabel('Phrase Length (segments)', fontsize=12)
    ax.set_ylabel('Mean IV Sum', fontsize=12)
    ax.set_title('Phrase Length vs Complexity', fontsize=14)
    plt.colorbar(scatter, ax=ax, label='Duration (sec)')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(PLOTS_DIR / 'phrase_summary.png', dpi=150)
    plt.close()
    print(f"  Saved: {PLOTS_DIR}/phrase_summary.png")


def main():
    print("Parker Corpus: Phrase Detection from MusicXML Rests")
    print("="*70)

    # Load segment data
    df = load_data(INPUT_CSV)

    # Extract rests from XML files
    rests_df = extract_all_rests(XML_DIR)

    # Analyze rest distribution
    analyze_rest_distribution(rests_df)

    # Test different minimum rest durations
    print("\n" + "="*70)
    print("TESTING MINIMUM REST DURATION FILTERS")
    print("="*70)

    min_durations = [0.0, 0.25, 0.5, 1.0]

    for min_dur in min_durations:
        df_with_boundaries = match_rests_to_segments(df, rests_df, min_duration_quarters=min_dur)
        boundary_count = df_with_boundaries['phrase_boundary_after'].sum()
        avg_phrase_len = len(df_with_boundaries) / (boundary_count + 1) if boundary_count > 0 else len(df_with_boundaries)

        print(f"\n  Min duration: {min_dur} quarters")
        print(f"    Phrase boundaries: {boundary_count}")
        print(f"    Avg segments/phrase: {avg_phrase_len:.1f}")

    # Use 8th note rest as minimum (0.5 quarters)
    print("\n" + "="*70)
    print("USING 0.5 QUARTER NOTE (8TH REST) AS MINIMUM")
    print("="*70)

    df_with_boundaries = match_rests_to_segments(df, rests_df, min_duration_quarters=0.5)

    # Create phrase dataset
    phrases_df = create_phrases(df_with_boundaries)

    # Save
    phrases_df.to_csv('parker_phrases.csv', index=False)
    print(f"\nSaved: parker_phrases.csv ({len(phrases_df)} phrases)")

    # Visualize examples
    visualize_phrases(df_with_boundaries, phrases_df, 'Cosmic Rays')
    visualize_phrases(df_with_boundaries, phrases_df, 'Si Si')

    # Annotate scores directly from XML
    xml_dir = Path(XML_DIR)
    for tune_name in ['Si Si', 'Cosmic Rays']:
        tune_id = phrases_df[phrases_df['tune'] == tune_name].iloc[0]['tune_id']
        xml_file = xml_dir / f"{tune_id}.xml"
        if xml_file.exists():
            annotate_score_with_phrases_from_rests(str(xml_file), min_duration_quarters=0.5)

    # Create phrase diagrams
    create_phrase_diagram(phrases_df, 'Si Si')
    create_phrase_diagram(phrases_df, 'Cosmic Rays')

    # Summary visualizations
    create_summary_visualization(phrases_df)

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nOutputs:")
    print(f"  - {PLOTS_DIR}/rest_distribution.png")
    print(f"  - {PLOTS_DIR}/Cosmic_Rays_phrases.png")
    print(f"  - {PLOTS_DIR}/Si_Si_phrases.png")
    print(f"  - {PLOTS_DIR}/Si_Si_annotated.xml")
    print(f"  - {PLOTS_DIR}/Cosmic_Rays_annotated.xml")
    print(f"  - {PLOTS_DIR}/Si_Si_phrase_diagram.png")
    print(f"  - {PLOTS_DIR}/Cosmic_Rays_phrase_diagram.png")
    print(f"  - {PLOTS_DIR}/phrase_summary.png")
    print(f"  - parker_phrases.csv")

    print("\nNext steps:")
    print("  - Review phrase visualizations and annotated scores")
    print("  - Use parker_phrases.csv for phrase-level rolling window analysis")
    print("  - Compute Granger causality and robustness metrics on phrases")


if __name__ == '__main__':
    main()
