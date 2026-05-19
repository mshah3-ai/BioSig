from __future__ import annotations

import argparse
import csv
import gzip
import time
from pathlib import Path

import numpy as np

from biosig.core import BiosigReader, encode_biosig
from biosig.edf import find_recording, read_edf_digital
from biosig.metrics import gzip_file, hdf5_selected_channels, save_raw_selected_channels


def file_size_mb(path: str | Path) -> float:
    return Path(path).stat().st_size / (1024 * 1024)


def time_biosig_random_reads(bsg_path: Path, windows: int, seconds: float) -> float:
    rng = np.random.default_rng(0)

    with BiosigReader(bsg_path) as reader:
        sr = reader.header.sample_rate
        window_samples = int(seconds * sr)
        max_start = max(1, reader.header.samples - window_samples - 1)
        starts = rng.integers(0, max_start, size=windows)

        t0 = time.perf_counter()

        for s in starts:
            reader.read_window(0, int(s), int(s) + window_samples)

        return (time.perf_counter() - t0) / windows


def time_raw_random_reads(raw_path: Path, shape: tuple[int, int], windows: int, seconds: float, sample_rate: float) -> float:
    rng = np.random.default_rng(0)

    arr = np.memmap(raw_path, dtype=np.int32, mode="r", shape=shape)

    window_samples = int(seconds * sample_rate)
    max_start = max(1, shape[1] - window_samples - 1)
    starts = rng.integers(0, max_start, size=windows)

    t0 = time.perf_counter()

    for s in starts:
        _ = np.asarray(arr[0, int(s): int(s) + window_samples])

    return (time.perf_counter() - t0) / windows


def time_gzip_random_reads(gzip_path: Path, shape: tuple[int, int], windows: int, seconds: float, sample_rate: float) -> float:
    rng = np.random.default_rng(0)

    window_samples = int(seconds * sample_rate)
    max_start = max(1, shape[1] - window_samples - 1)
    starts = rng.integers(0, max_start, size=windows)

    t0 = time.perf_counter()

    for s in starts:
        with gzip.open(gzip_path, "rb") as f:
            raw = f.read()

        arr = np.frombuffer(raw, dtype=np.int32).reshape(shape)
        _ = arr[0, int(s): int(s) + window_samples]

    return (time.perf_counter() - t0) / windows


def time_hdf5_random_reads(h5_path: Path, windows: int, seconds: float, sample_rate: float) -> float | None:
    try:
        import h5py
    except ImportError:
        return None

    rng = np.random.default_rng(0)

    with h5py.File(h5_path, "r") as f:
        dset = f["signals"]
        samples = dset.shape[1]

        window_samples = int(seconds * sample_rate)
        max_start = max(1, samples - window_samples - 1)
        starts = rng.integers(0, max_start, size=windows)

        t0 = time.perf_counter()

        for s in starts:
            _ = dset[0, int(s): int(s) + window_samples]

        return (time.perf_counter() - t0) / windows


def biosignal_delta_stats(signals: np.ndarray) -> dict:
    deltas = np.diff(signals, axis=1).reshape(-1)

    total = deltas.size

    if total == 0:
        return {
            "pct_fit_4_bits": 0.0,
            "pct_fit_8_bits": 0.0,
            "pct_fit_16_bits": 0.0,
        }

    return {
        "pct_fit_4_bits": float(np.mean((-8 <= deltas) & (deltas <= 7)) * 100),
        "pct_fit_8_bits": float(np.mean((-128 <= deltas) & (deltas <= 127)) * 100),
        "pct_fit_16_bits": float(np.mean((-32768 <= deltas) & (deltas <= 32767)) * 100),
    }


def write_seekability_plot(rows: list[dict], output_path: Path) -> None:
    import matplotlib.pyplot as plt

    methods = [r["method"] for r in rows]
    times = [float(r["avg_random_window_read_seconds"]) for r in rows]

    plt.figure(figsize=(8, 4.5))
    plt.bar(methods, times)
    plt.ylabel("Average seconds per random 30s window")
    plt.title("Seekability comparison")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def write_biosignal_awareness_plot(stats: dict, output_path: Path) -> None:
    import matplotlib.pyplot as plt

    labels = ["4-bit deltas", "8-bit deltas", "16-bit deltas"]
    values = [
        stats["pct_fit_4_bits"],
        stats["pct_fit_8_bits"],
        stats["pct_fit_16_bits"],
    ]

    plt.figure(figsize=(7, 4.5))
    plt.bar(labels, values)
    plt.ylabel("% of inter-sample deltas")
    plt.ylim(0, 100)
    plt.title("Biosignal-aware delta structure")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def write_advantage_table(rows: list[dict], output_path: Path) -> None:
    fieldnames = [
        "method",
        "size_mb",
        "avg_random_window_read_seconds",
        "seekable",
        "streamable",
        "simple",
        "biosignal_aware",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir")
    parser.add_argument("--recording")
    parser.add_argument("--output-dir", default="figures")
    parser.add_argument("--max-channels", type=int, default=3)
    parser.add_argument("--windows", type=int, default=50)
    parser.add_argument("--window-seconds", type=float, default=30.0)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    recording = Path(args.recording) if args.recording else find_recording(args.data_dir)

    signals, meta = read_edf_digital(recording, max_channels=args.max_channels)

    raw_path = output_dir / f"{recording.stem}.selected_raw_i32"
    gzip_path = output_dir / f"{recording.stem}.selected_raw_i32.gz"
    h5_path = output_dir / f"{recording.stem}.selected_channels.h5"
    bsg_path = output_dir / f"{recording.stem}.bsg"

    save_raw_selected_channels(signals, raw_path)
    gzip_file(raw_path, gzip_path)

    encode_biosig(
        signals,
        bsg_path,
        sample_rate=meta["sample_rate"],
        channel_names=meta["channel_names"],
        physical_dimensions=meta["physical_dimensions"],
        keyframe_interval=256,
        source=meta["source"],
    )

    h5_result = hdf5_selected_channels(signals, meta, h5_path)

    shape = signals.shape
    sample_rate = float(meta["sample_rate"])

    rows = []

    rows.append(
        {
            "method": "raw selected channels",
            "size_mb": file_size_mb(raw_path),
            "avg_random_window_read_seconds": time_raw_random_reads(
                raw_path,
                shape,
                args.windows,
                args.window_seconds,
                sample_rate,
            ),
            "seekable": "yes",
            "streamable": "yes",
            "simple": "yes",
            "biosignal_aware": "no",
        }
    )

    rows.append(
        {
            "method": "gzip raw selected channels",
            "size_mb": file_size_mb(gzip_path),
            "avg_random_window_read_seconds": time_gzip_random_reads(
                gzip_path,
                shape,
                args.windows,
                args.window_seconds,
                sample_rate,
            ),
            "seekable": "no",
            "streamable": "limited",
            "simple": "yes",
            "biosignal_aware": "no",
        }
    )

    rows.append(
        {
            "method": "biosig",
            "size_mb": file_size_mb(bsg_path),
            "avg_random_window_read_seconds": time_biosig_random_reads(
                bsg_path,
                args.windows,
                args.window_seconds,
            ),
            "seekable": "yes",
            "streamable": "yes",
            "simple": "yes",
            "biosignal_aware": "yes",
        }
    )

    if h5_result is not None:
        h5_time = time_hdf5_random_reads(
            h5_path,
            args.windows,
            args.window_seconds,
            sample_rate,
        )

        rows.append(
            {
                "method": "HDF5 gzip selected channels",
                "size_mb": file_size_mb(h5_path),
                "avg_random_window_read_seconds": h5_time,
                "seekable": "yes",
                "streamable": "limited",
                "simple": "no",
                "biosignal_aware": "no",
            }
        )

    delta_stats = biosignal_delta_stats(signals)

    advantage_csv = output_dir / "advantage_table.csv"
    seek_plot = output_dir / "seekability_comparison.png"
    bio_plot = output_dir / "biosignal_awareness.png"

    write_advantage_table(rows, advantage_csv)
    write_seekability_plot(rows, seek_plot)
    write_biosignal_awareness_plot(delta_stats, bio_plot)

    print(f"Recording: {recording}")
    print(f"Wrote {advantage_csv}")
    print(f"Wrote {seek_plot}")
    print(f"Wrote {bio_plot}")
    print()
    print("Delta statistics:")
    for k, v in delta_stats.items():
        print(f"{k}: {v:.2f}%")
    print()
    print("Seekability:")
    for row in rows:
        print(
            f"{row['method']}: "
            f"{float(row['avg_random_window_read_seconds']):.6f} sec/window"
        )


if __name__ == "__main__":
    main()