# Charlie Parker Time Series Analysis Pipeline

Computational time series analysis of Charlie Parker's improvisational practice examining temporal evolution of harmonic material across multiple scales.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📄 Paper

**Rubini, M.** (2025). "Bird" Over Time: a Time Series Analysis of Charlie Parker's Harmonic Complexity

**Abstract:** This study presents a computational time series analysis of Charlie Parker's improvisational practice using the complete Charlie Parker Omnibook corpus. We develop metrics for harmonic complexity, dissonance, and rate of change, then examine temporal patterns through phrase-level analysis, rolling windows, autocorrelation, K-means clustering, Granger causality testing, and triadic content analysis. Our analysis reveals Parker's improvisation as reactive navigation where dissonance predicts subsequent complexity (17.4% of tunes show significant causality), and demonstrates that mastery emerges through strategic use of triadically sparse sonorities rather than accumulation of exotic materials.

---

## 🎯 Overview

This pipeline analyzes 50 Charlie Parker performances from the Omnibook corpus using:

- **Interval Vector Analysis**: Mathematical representation of harmonic content
- **Time Series Methods**: Tracking evolution of complexity, dissonance, and rate of change
- **Phrase Detection**: Using actual rests from MusicXML transcriptions
- **Multi-Scale Analysis**: From segment-level (individual chords) to chorus-level structure
- **Statistical Methods**: Autocorrelation, K-means clustering, Granger causality testing
- **Network Analysis**: Harmonic vocabulary as navigational network
- **Robustness Analysis**: Triadic content as structural flexibility metric

### Key Findings

1. **Reactive Navigation**: Parker responds to dissonance by escalating complexity (Dissonance → Complexity: 17.4% significant causality vs. 8.7% reverse)
2. **Four Improvisational Strategies**: Balanced, Contrasting, Exploratory, and Volatile/Continuous
3. **Triadic Sparsity**: Most frequent interval vectors are triadically sparse (r = -0.22), contradicting pedagogical emphasis on upper-structure harmony
4. **Hub-Centric Vocabulary**: IV (111000) appears 226 times as navigational pivot, not functional foundation

---

## 🔧 Requirements

- Python 3.10 or higher
- Required packages (see `requirements.txt`):
```
  pandas>=2.0.0
  numpy>=1.24.0
  matplotlib>=3.7.0
  seaborn>=0.12.0
  statsmodels>=0.14.0
  scikit-learn>=1.3.0
  networkx>=3.1
  lxml>=4.9.0
  music21>=8.3.0
  scipy>=1.10.0
```

---

## 📦 Installation
```bash
# Clone repository
git clone https://github.com/mikerubini/parker-timeseries.git
cd parker-timeseries

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 📁 Data Setup

### Required Data (Not Included - Copyright Protected)

This analysis requires the **Charlie Parker Aligned Digital Omnibook** dataset:

1. **MusicXML transcriptions** - Manual and automatic transcriptions
2. **MIDI alignment files** - Precise timestamps

**How to obtain:**
- Contact: Inria (Ken Déguernel, Emmanuel Vincent) / STMS Lab Ircam/CNRS/UPMC
- Original data: [Parker Omnibook Dataset](https://repmus.ircam.fr/_media/online-publications/degraduernel2016using.pdf)
- License: CC BY-NC-SA 2.0
- Original copyrights: Atlantic Music Corp.

### Directory Structure

Place obtained data in these directories:
```
parker-timeseries/
├── xml/              # MusicXML files (*.xml)
├── midi/             # MIDI alignment files (*.mid)
├── 00_match_titles.py
├── 01_process.py
├── ...
└── README.md
```

---

## 🚀 Usage

### Quick Start

Run scripts in numerical order. Each script builds on outputs from previous scripts:
```bash
python 00_match_titles.py      # Match XML/MIDI files to tune titles
python 01_process.py            # Extract pitch classes and compute IVs
python 02_align_midi.py         # Align segments with MIDI timestamps
python 03_timeseries_analysis.py # Compute complexity, dissonance, IV distance
# ... continue through 11_robustness.py
```

### Individual Script Execution

Each script is self-contained and includes progress output:
```bash
python 07_phrase_detection.py
# Output:
# Loaded 3,024 segments from 46 tunes
# Extracting rests from MusicXML files...
# Created 1,507 phrases across 46 tunes
# Saved: parker_phrases.csv
```

---

## 📊 Pipeline

### Visual Overview

![Pipeline Diagram](pipeline2.html) *(Open in browser for interactive visualization)*

### Script Details

#### **00_match_titles.py**
- **Purpose**: Match XML file IDs to tune titles
- **Input**: `xml/` directory
- **Output**: `tune_titles.csv`

#### **01_process.py**
- **Purpose**: Extract pitch classes per chord, compute interval vectors
- **Input**: `xml/` directory, `tune_titles.csv`
- **Output**: `parker_sequential.csv` (3,371 segments)
- **Key Concept**: One IV per chord change

#### **02_align_midi.py**
- **Purpose**: Align segments with MIDI timestamps for time series analysis
- **Input**: `parker_sequential.csv`, `midi/` directory
- **Output**: `parker_timeseries.csv` (3,024 segments with timestamps, 46 tunes)
- **Note**: 4 tunes fail alignment (missing MIDI files)

#### **03_timeseries_analysis.py**
- **Purpose**: Compute temporal metrics per segment
- **Metrics**:
  - Complexity: `iv_sum = Σ ic_i`
  - Dissonance: `ic₁ + 0.5·ic₂ + 0.8·ic₆`
  - Rate of Change: `√Σ(ic_i^(t+1) - ic_i^t)²`
- **Output**: Updated `parker_timeseries.csv`, visualization plots

#### **04_timeseries_plot_highlhigh.py** & **04_timeseries...plot_highlow.py**
- **Purpose**: Generate time series visualizations for selected tunes
- **Output**: Individual tune plots showing complexity evolution

#### **05_chorus_analysis.py**
- **Purpose**: Analyze complexity evolution across chorus structure
- **Output**: Cross-chorus comparison plots, form-normalized overlays

#### **06_expansion.py**
- **Purpose**: Detect anomalies and expansion patterns
- **Output**: Anomaly analysis plots

#### **07_phrase_detection.py** ⭐
- **Purpose**: Detect phrase boundaries using actual MusicXML rests
- **Method**: 
  - Parse `<rest>` elements (≥0.5 quarter notes)
  - Hierarchical matching to segments
  - Aggregate segment metrics into phrase-level statistics
- **Output**: `parker_phrases.csv` (1,507 phrases)
- **Key Innovation**: Uses actual rests, not inferred pauses

#### **08_rolling_windows.py**
- **Purpose**: Compute rolling window statistics (local dynamics)
- **Windows**: 3, 5, 10 phrases
- **Metrics**: Rolling mean, std, CV (coefficient of variation)
- **Output**: `parker_robustness_metrics.csv`, rolling window plots

#### **09_autocorrelation.py** ⭐
- **Purpose**: Compute phrase-to-phrase predictability
- **Method**: Pearson correlation at lags 1-5
- **Formula**: `r_k = cor(x_t, x_(t+k))`
- **Output**: `parker_autocorrelation_metrics.csv`, autocorrelation profiles

#### **10_gravity.py** ⭐
- **Purpose**: Test directional causal relationships (Gravity)
- **Tests**:
  1. Complexity → Dissonance
  2. Dissonance → Complexity
  3. Phrase Length → Complexity
  4. Phrase Length → Dissonance
- **Method**: Granger causality F-tests (lags 1-3)
- **Output**: `parker_granger_results.csv`, causality heatmaps
- **Key Finding**: Dissonance → Complexity dominant (17.4% significant)

#### **11_robustness.py** ⭐
- **Purpose**: Analyze triadic content (Global Robustness)
- **Method**: Count major, minor, dim, aug triads per IV
- **Output**: `parker_iv_robustness.csv`, robustness scatter plots
- **Key Finding**: Frequent IVs are triadically sparse (r = -0.22)

### Clustering (Embedded in 09_autocorrelation.py)

K-means clustering identifies **four improvisational strategies**:

1. **Cluster 0 - Balanced/Moderate** (25 tunes)
   - Moderate complexity, volatility, positive autocorr
   
2. **Cluster 1 - Contrasting** (13 tunes)
   - Moderate complexity, negative autocorr (alternating phrases)
   
3. **Cluster 2 - Exploratory/Episodic** (7 tunes)
   - High complexity, high volatility, low autocorr
   
4. **Cluster 3 - Volatile/Continuous** (1 tune: "My Little Suede Shoes")
   - LOW complexity, EXTREME volatility, HIGH autocorr (paradox)

**Output**: `parker_cluster_assignments.csv`

---

## 📤 Output Files

### Core Data Files

| File | Rows | Description |
|------|------|-------------|
| `tune_titles.csv` | 50 | File ID to tune title mapping |
| `parker_sequential.csv` | 3,371 | All segments with IVs |
| `parker_timeseries.csv` | 3,024 | 46 tunes with timestamps + metrics |
| `parker_phrases.csv` | 1,507 | Phrase-level aggregated data |

### Analysis Results

| File | Description |
|------|-------------|
| `parker_robustness_metrics.csv` | Per-tune volatility, CV metrics |
| `parker_autocorrelation_metrics.csv` | Autocorr lags 1-5 per tune |
| `parker_cluster_assignments.csv` | Strategy cluster (0-3) per tune |
| `parker_granger_results.csv` | F-stats, p-values for causality tests |
| `parker_iv_robustness.csv` | Triadic content per unique IV |

### Visualizations

Output directories created automatically:
- `03_timeseries_plots/`
- `04_form_plots/`
- `07_phrase_plots/`
- `08_rolling_window_plots/`
- `09_autocorr_clustering_plots/`
- `10_granger_plots/`
- `11_robustness_plots/`

---

## 🔬 Methodology Highlights

### Interval Vectors

Interval vectors abstract pitch-class sets into 6-dimensional vectors counting interval class occurrences:
```
IV = (ic₁, ic₂, ic₃, ic₄, ic₅, ic₆)

Example: {C, C♯, E♭} → (111000)
- C → C♯ = 1 semitone (ic₁)
- C → E♭ = 3 semitones (ic₃)
- C♯ → E♭ = 2 semitones (ic₂)
```

This abstraction:
- Discards voice-leading and temporal ordering
- Captures harmonic resource selection
- Enables cross-performance comparison
- Suitable for navigation analysis (not trajectory)

### Phrase Detection Innovation

Traditional methods infer phrases from timestamp gaps. We use **actual rests from MusicXML**:
```python
# Parse <rest> elements with durations ≥ 0.5 quarter notes
# Match to harmonic segments hierarchically
# Respects Parker's actual articulation as transcribed
```

### Granger Causality ("Gravity")

Measures **predictive asymmetry**, not true causation:

- Does past dissonance improve prediction of future complexity?
- Beyond complexity's own autoregressive history?
- Reveals reactive vs. proactive patterns

**Interpretation**: Significant Dissonance → Complexity means Parker responds to harmonic tension by escalating complexity.

---

## 📚 Citation

If you use this code or data in your research, please cite:
```bibtex
@article{rubini2025parker,
  title={Temporal Evolution of Harmonic Material in Jazz Improvisation: A Multi-Scale Analysis of Charlie Parker's Practice},
  author={Rubini, Mike},
  journal={[Journal Name]},
  year={2025},
  doi={[DOI]}
}

@software{rubini2025parker_code,
  author={Rubini, Mike},
  title={Charlie Parker Time Series Analysis Pipeline},
  year={2025},
  publisher={Zenodo},
  doi={10.5281/zenodo.XXXXXX},
  url={https://github.com/mikerubini/parker-timeseries}
}
```

---

## 📜 License

**Code**: MIT License - See [LICENSE](LICENSE) file

**Data**: Original transcriptions under CC BY-NC-SA 2.0 (Déguernel, Vincent, Assayag). Copyrights held by Atlantic Music Corp. Data not redistributed in this repository.

---

## 🙏 Acknowledgments

- **Dataset**: Ken Déguernel, Emmanuel Vincent, Gérard Assayag (Inria, STMS Lab Ircam/CNRS/UPMC)
- **MIDI Alignment**: Ben Riley, Simon Dixon
- **Original Transcriptions**: Charlie Parker Omnibook © Atlantic Music Corp.

### References

- Déguernel, K., Vincent, E., & Assayag, G. (2016). "Using Multidimensional Sequences for Improvisation in the OMax Paradigm." *Proceedings of the 13th Sound and Music Computing Conference*.
- Riley, B., & Dixon, S. (2024). "Reconstructing Charlie Parker's Improvisational Vocabulary through Automatic Transcription."

---

## 📧 Contact

**Mike Rubini**
- Website: [music.mikerubini.com](https://music.mikerubini.com)
- Email: music@mikerubini.com
- GitHub: [@code91](https://github.com/code91)

## 🐛 Issues & Contributions

Issues and pull requests welcome! Please open an issue to discuss major changes before submitting PRs.

### Known Limitations

- Phrase detection relies on transcribed rest notation (transcriber interpretation)
- Interval vectors discard voice-leading and melodic ordering
- Granger causality measures statistical precedence, not cognitive intent
- Triadic robustness uses heuristic estimation for large cardinality sets
- Corpus represents Omnibook transcriptions, not complete Parker practice

---

## 📊 Example Results

### Vocabulary Hub: (111000)

The chromatic trichord (111000) appears 226 times as the navigational hub:
```
Voicings: {C, C♯, E♭}, {C, D, E♭}, {C, A, B♭}
Functions: II (51), I (48), V (44) - highly versatile
Transitions: Bidirectional with (122010) [II ↔ I]
```

### Four Strategies

| Strategy | Tunes | Key Characteristics |
|----------|-------|---------------------|
| Balanced | 25 | Moderate complexity, positive autocorr |
| Contrasting | 13 | Negative autocorr (phrase alternation) |
| Exploratory | 7 | High complexity, low autocorr (episodic) |
| Volatile/Continuous | 1 | Low complexity, high volatility, high autocorr |

### Gravity (Granger Causality)
```
Dissonance → Complexity: 17.4% significant (reactive navigation)
Complexity → Dissonance:  8.7% significant
Ratio: 2:1 - Parker responds to tension, doesn't create it proactively
```

---

**Last Updated**: December 2025
**Version**: 1.0.0
