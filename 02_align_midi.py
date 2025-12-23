"""
MIDI Timestamp Alignment
========================

Align sequential segment data with timestamps from aligned MIDI files.

Usage:
    python 2_align_midi.py

Inputs:
    - parker_sequential.csv (from process_corpus.py)
    - midi/{id}-fine-aligned.mid files

Output:
    - parker_sequential_aligned.csv (with timestamp_ms column)
"""

import csv
import os
from pathlib import Path
from collections import defaultdict

try:
    import mido
except ImportError:
    print("Installing mido...")
    os.system("pip install mido --break-system-packages")
    import mido


def parse_midi_timing(midi_path):
    """
    Parse MIDI file and build a mapping of (measure, beat) -> timestamp_ms.
    
    Returns:
        Tuple of (ticks_per_beat, tempo_map, time_signature_map, total_ticks)
    """
    mid = mido.MidiFile(midi_path)
    ticks_per_beat = mid.ticks_per_beat
    
    # Collect tempo changes and time signatures
    tempo_changes = []  # [(tick, tempo_us), ...]
    time_sig_changes = []  # [(tick, numerator, denominator), ...]
    
    current_tick = 0
    for track in mid.tracks:
        current_tick = 0
        for msg in track:
            current_tick += msg.time
            if msg.type == 'set_tempo':
                tempo_changes.append((current_tick, msg.tempo))
            elif msg.type == 'time_signature':
                time_sig_changes.append((current_tick, msg.numerator, msg.denominator))
    
    # Default tempo (120 BPM = 500000 us/beat) and time signature (4/4)
    if not tempo_changes:
        tempo_changes = [(0, 500000)]
    if not time_sig_changes:
        time_sig_changes = [(0, 4, 4)]
    
    # Sort by tick
    tempo_changes.sort(key=lambda x: x[0])
    time_sig_changes.sort(key=lambda x: x[0])
    
    return ticks_per_beat, tempo_changes, time_sig_changes, mid


def tick_to_ms(tick, ticks_per_beat, tempo_changes):
    """Convert MIDI tick to milliseconds, accounting for tempo changes."""
    ms = 0.0
    prev_tick = 0
    current_tempo = tempo_changes[0][1]  # microseconds per beat
    
    for change_tick, tempo in tempo_changes:
        if change_tick >= tick:
            break
        # Add time from prev_tick to change_tick at current tempo
        delta_ticks = change_tick - prev_tick
        delta_beats = delta_ticks / ticks_per_beat
        delta_ms = delta_beats * (current_tempo / 1000.0)
        ms += delta_ms
        prev_tick = change_tick
        current_tempo = tempo
    
    # Add remaining time from last tempo change to target tick
    delta_ticks = tick - prev_tick
    delta_beats = delta_ticks / ticks_per_beat
    delta_ms = delta_beats * (current_tempo / 1000.0)
    ms += delta_ms
    
    return ms


def measure_beat_to_tick(measure, beat, ticks_per_beat, time_sig_changes):
    """
    Convert measure.beat to MIDI ticks.
    
    Args:
        measure: 1-indexed measure number
        beat: 0-indexed beat within measure
        ticks_per_beat: MIDI ticks per beat
        time_sig_changes: List of (tick, numerator, denominator) tuples
    
    Returns:
        Tick position
    """
    # Build measure boundaries
    # This is simplified - assumes mostly consistent time signatures
    
    # Get the predominant time signature (usually 4/4 for jazz)
    if time_sig_changes:
        numerator, denominator = time_sig_changes[0][1], time_sig_changes[0][2]
    else:
        numerator, denominator = 4, 4
    
    # Beats per measure
    beats_per_measure = numerator
    
    # Calculate tick
    # measure is 1-indexed, beat is 0-indexed
    total_beats = (measure - 1) * beats_per_measure + beat
    tick = int(total_beats * ticks_per_beat)
    
    return tick


def build_measure_beat_to_ms_map(midi_path):
    """
    Build a complete mapping from (measure, beat) to milliseconds for a MIDI file.
    
    Returns:
        Function that takes (measure, beat) and returns timestamp_ms
    """
    ticks_per_beat, tempo_changes, time_sig_changes, mid = parse_midi_timing(midi_path)
    
    def get_timestamp(measure, beat):
        tick = measure_beat_to_tick(measure, beat, ticks_per_beat, time_sig_changes)
        ms = tick_to_ms(tick, ticks_per_beat, tempo_changes)
        return ms
    
    return get_timestamp


def align_sequential_data(input_csv, midi_dir, output_csv):
    """
    Add timestamp_ms column to sequential data by aligning with MIDI files.
    
    Args:
        input_csv: Path to parker_sequential.csv
        midi_dir: Path to folder containing MIDI files
        output_csv: Path for output CSV with timestamps
    """
    midi_path = Path(midi_dir)
    
    # Load input data
    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    print(f"Loaded {len(rows)} segments from {input_csv}")
    
    # Group by tune ID
    tunes = defaultdict(list)
    for i, row in enumerate(rows):
        tunes[row['id']].append((i, row))
    
    print(f"Found {len(tunes)} unique tunes")
    
    # Process each tune
    aligned_count = 0
    failed_tunes = []
    
    for tune_id, segments in tunes.items():
        midi_file = midi_path / f"{tune_id}-fine-aligned.mid"
        
        if not midi_file.exists():
            print(f"  {tune_id}: MIDI not found, skipping")
            failed_tunes.append(tune_id)
            for i, row in segments:
                rows[i]['timestamp_ms'] = ''
            continue
        
        try:
            get_timestamp = build_measure_beat_to_ms_map(str(midi_file))
            
            for i, row in segments:
                measure = int(row['measure'])
                beat = float(row['beat'])
                timestamp_ms = get_timestamp(measure, beat)
                rows[i]['timestamp_ms'] = f"{timestamp_ms:.1f}"
                aligned_count += 1
            
            # Print first segment timestamp for verification
            first_seg = segments[0][1]
            first_ts = rows[segments[0][0]]['timestamp_ms']
            print(f"  {tune_id} ({first_seg['tune']}): {len(segments)} segments aligned, first at {first_ts}ms")
            
        except Exception as e:
            print(f"  {tune_id}: ERROR - {e}")
            failed_tunes.append(tune_id)
            for i, row in segments:
                rows[i]['timestamp_ms'] = ''
    
    # Write output
    output_fieldnames = fieldnames + ['timestamp_ms']
    
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nAligned {aligned_count} segments")
    if failed_tunes:
        print(f"Failed tunes: {failed_tunes}")
    print(f"Output: {output_csv}")


def main():
    input_csv = 'parker_sequential.csv'
    midi_dir = 'midi'
    output_csv = 'parker_sequential_aligned.csv'
    
    align_sequential_data(input_csv, midi_dir, output_csv)


if __name__ == '__main__':
    main()
