# BioSig

*A seekable, streaming-friendly, delta-encoded binary format for physiological time-series data (EEG, ECG, EMG).*

BioSig is a lightweight binary storage format designed specifically for biosignal workloads. It combines lossless temporal delta encoding, block-level random access, and dependency-light decoding to provide substantially smaller storage than raw signal arrays while remaining dramatically faster than gzip for random-access window reads.

Unlike generic compression formats, BioSig is biosignal-aware: it directly exploits the smooth temporal structure of physiological signals using delta encoding and bit-packed block storage.

---

## Features

- Lossless compression for EEG/ECG/EMG-style signals
- Fast random-access window decoding
- Streaming-friendly block structure
- Delta + bit-packed temporal encoding
- Keyframe-indexed seekability
- Tiny dependency-light format
- Simple binary spec suitable for reimplementation in C/Rust
- Python CLI + API
- Benchmark and visualization suite included

---

# Quick Start

## Installation

```bash
pip install -e ".[dev,bench]"
```

---

## Convert EDF/REC → BioSig

```bash
biosig convert path/to/file.rec output.bsg
```

Example:

```bash
biosig convert SC4002E0.rec sample.bsg
```

---

## Inspect a BioSig file

```bash
biosig info sample.bsg
```

---

## Read a signal window

```bash
biosig slice sample.bsg \
  --channel 0 \
  --start 30 \
  --end 90 \
  --output slice.csv
```

This extracts a 60-second segment from channel 0.

---

# Format Overview

BioSig stores signals as:

```text
absolute keyframe
+ delta encoded samples
+ bit-packed blocks
```

The format is optimized for smooth temporal signals where adjacent samples change gradually.

---

## Encoding Pipeline

```text
raw signal
→ delta encoding
→ adaptive block sizing
→ bit-packed signed deltas
→ indexed binary stream
```

---

## Core Design Goals

| Goal | BioSig |
|---|---|
| Lossless | Yes |
| Random-access decoding | Yes |
| Streaming-friendly | Yes |
| Dependency-light | Yes |
| Biosignal-aware | Yes |
| Human-readable spec | Yes |

---

# Why BioSig?

Generic compression formats optimize primarily for final filesize.

BioSig instead optimizes for the workloads common in physiological time-series analysis:

- random window extraction
- streaming
- large archival datasets
- channel slicing
- interactive analysis pipelines
- low-overhead decoding

This makes BioSig especially suitable for:
- sleep EEG datasets
- long-term ECG recordings
- neural recordings
- wearable biosensors
- edge/embedded analysis systems

---

# Benchmark Results

Benchmarks were generated on Sleep-EDF recordings using 3 selected channels.

## Compression Comparison

| Method | Size (MB) | Compression Ratio |
|---|---:|---:|
| Raw selected channels | 97.16 | 1.00x |
| gzip raw selected channels | 39.46 | 2.46x |
| BioSig | 50.14 | 1.94x |
| HDF5 gzip selected channels | 40.66 | 2.39x |

### Storage Comparison

![Storage Comparison](figures/storage_comparison.png)

BioSig achieves nearly 2× lossless compression relative to raw storage while remaining fully seekable and streaming-friendly.

---

## Random-Access Seekability

| Method | Avg Random Window Read |
|---|---:|
| Raw selected channels | 0.00000147 s |
| gzip raw selected channels | 0.471936 s |
| BioSig | 0.000077 s |
| HDF5 gzip selected channels | 0.000257 s |

### Key Results

- BioSig random-access reads are approximately:
  - **~6110× faster than gzip**
  - **~3.3× faster than HDF5 gzip**
- BioSig remains:
  - seekable
  - streaming-friendly
  - dependency-light
  - biosignal-aware

---

# Tradeoff Profile

| Method | Compression | Random Access | Streaming | Simplicity | Biosignal-Aware |
|---|---|---|---|---|---|
| Raw EDF-style storage | Poor | Excellent | Excellent | Excellent | No |
| gzip | Excellent | Poor | Limited | Excellent | No |
| HDF5 gzip | Excellent | Good | Limited | Moderate | No |
| BioSig | Good | Excellent | Excellent | Excellent | Yes |

BioSig intentionally trades a modest compression penalty for dramatically faster random-access decoding and a radically simpler format.

---

# CLI Commands

| Command | Description |
|---|---|
| `biosig convert <input.rec> <output.bsg>` | Convert EDF/REC → BioSig |
| `biosig info <file.bsg>` | Inspect metadata |
| `biosig slice <file.bsg>` | Extract signal windows |
| `python scripts/run_all_figures.py ...` | Generate benchmark figures |
| `python benchmark/benchmark_advantages.py ...` | Run seekability benchmarks |

---

# Python API

```python
from biosig.core import encode_biosig, BiosigReader

encode_biosig(
    signals,
    "sample.bsg",
    sample_rate=256,
)

with BiosigReader("sample.bsg") as reader:
    window = reader.read_window(
        channel=0,
        start_sample=1000,
        stop_sample=5000,
    )
```

---

# Repository Structure

```text
biosig/
├── biosig/
│   ├── core.py
│   ├── convert.py
│   ├── cli.py
│   ├── edf.py
│   └── metrics.py
│
├── benchmark/
│   └── benchmark_advantages.py
│
├── scripts/
│   └── run_all_figures.py
│
├── tests/
│   └── test_core.py
│
├── figures/
├── README.md
├── pyproject.toml
└── LICENSE
```

---

# Experimental Format Notes

BioSig is currently an experimental research/prototype format.

Current implemented features:

- delta encoding
- adaptive integer block storage
- sub-byte bit-packing
- keyframe indexing
- random-access decoding

Planned future work:

- delta-of-delta encoding
- entropy coding
- adaptive block sizing
- SIMD decoding
- multichannel predictive coding
- streaming network protocol
- Rust/C implementations

---

# Running Benchmarks

Generate all benchmark figures:

```bash
python scripts/run_all_figures.py \
  path/to/sleep-edf-database \
  --max-channels 3
```

Run advanced seekability benchmarks:

```bash
python benchmark/benchmark_advantages.py \
  path/to/sleep-edf-database \
  --max-channels 3
```

---

# Documentation

| File | Description |
|---|---|
| `README.md` | Project overview |
| `biosig/core.py` | Encoder/decoder implementation |
| `benchmark/benchmark_advantages.py` | Random-access benchmarks |
| `scripts/run_all_figures.py` | Figure generation pipeline |

---

# License

MIT License.

See `LICENSE` for details.
