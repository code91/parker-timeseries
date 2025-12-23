"""
Extract tune titles from MP3 metadata to create ID-to-title mapping.

Usage:
    python extract_titles.py mp3_folder output.csv
"""

import os
import csv
import sys
from pathlib import Path

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3
except ImportError:
    print("Installing mutagen...")
    os.system("pip install mutagen --break-system-packages")
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3


def extract_titles(mp3_dir, output_csv):
    """
    Extract titles from MP3 files and save to CSV.
    
    Args:
        mp3_dir: Path to folder containing MP3 files
        output_csv: Path to output CSV file
    """
    mp3_path = Path(mp3_dir)
    mp3_files = sorted(mp3_path.glob('*.mp3'))
    
    print(f"Found {len(mp3_files)} MP3 files\n")
    
    results = []
    
    for mp3_file in mp3_files:
        file_id = mp3_file.stem  # e.g., "2RfYc"
        
        try:
            audio = MP3(str(mp3_file))
            tags = audio.tags
            
            # Try different tag formats for title
            title = None
            artist = None
            album = None
            
            if tags:
                # ID3v2 tags
                if 'TIT2' in tags:
                    title = str(tags['TIT2'])
                if 'TPE1' in tags:
                    artist = str(tags['TPE1'])
                if 'TALB' in tags:
                    album = str(tags['TALB'])
            
            results.append({
                'id': file_id,
                'title': title or file_id,
                'artist': artist or '',
                'album': album or ''
            })
            
            print(f"{file_id} -> {title or '(no title)'}")
            
        except Exception as e:
            print(f"{file_id} -> ERROR: {e}")
            results.append({
                'id': file_id,
                'title': file_id,
                'artist': '',
                'album': ''
            })
    
    # Write CSV
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'title', 'artist', 'album'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\nExported {len(results)} entries to {output_csv}")
    
    return results


def main():
    if len(sys.argv) < 2:
        mp3_dir = 'mp3'
        output_csv = 'tune_titles.csv'
    elif len(sys.argv) == 2:
        mp3_dir = sys.argv[1]
        output_csv = 'tune_titles.csv'
    else:
        mp3_dir = sys.argv[1]
        output_csv = sys.argv[2]
    
    extract_titles(mp3_dir, output_csv)


if __name__ == '__main__':
    main()
