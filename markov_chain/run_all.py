"""
Run every step of the Markov-chain analysis pipeline in order:

    extract_notes.py
    01_transition_matrices.py
    02_stationary.py
    03_spectral.py
    04_hitting_times.py
    05_voice_leading.py
    06_null_comparison.py
    07_memory_order.py
    08_hub_structure.py
    09_generative_validation.py
    10_distribution_evolution.py
    11_graph_view.py
    12_direction.py
    build_presentation_data.py

Each step writes its artifacts to data/ and figures/.  The pipeline is
deterministic (RNG_SEED = 42 throughout) and reproducible from a fresh
checkout: delete data/ and figures/, then `python markov_chain/run_all.py`.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

STEPS = [
    "extract_notes.py",
    "01_transition_matrices.py",
    "02_stationary.py",
    "03_spectral.py",
    "04_hitting_times.py",
    "05_voice_leading.py",
    "06_null_comparison.py",
    "07_memory_order.py",
    "08_hub_structure.py",
    "09_generative_validation.py",
    "10_distribution_evolution.py",
    "11_graph_view.py",
    "12_direction.py",
    "build_presentation_data.py",
]


def main() -> None:
    total_start = time.time()
    for step in STEPS:
        path = HERE / step
        print("\n" + "=" * 72)
        print(f"[run_all]  $ python {path.relative_to(HERE.parent)}")
        print("=" * 72)
        t0 = time.time()
        result = subprocess.run([sys.executable, str(path)])
        elapsed = time.time() - t0
        if result.returncode != 0:
            print(f"\n[run_all] ✗ {step} failed with exit code {result.returncode}")
            sys.exit(result.returncode)
        print(f"\n[run_all] ✓ {step} completed in {elapsed:.1f}s")
    print(f"\n[run_all] ALL STEPS COMPLETE in {time.time() - total_start:.1f}s")


if __name__ == "__main__":
    main()
