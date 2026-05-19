from __future__ import annotations

import gzip
import shutil
import time
from pathlib import Path

import numpy as np

from .core import BiosigReader, encode_biosig
from .edf import read_edf_digital


def file_size_mb(path: str | Path) -> float:
    return Path(path).stat().st_size / (1024 * 1024)


def gzip_file(input_path: str | Path, output_path: str | Path) -> Path:
    input_path = Path(input_path)
    output_path = Path(output_path)

    with input_path.open("rb") as src, gzip.open(output_path, "wb", compresslevel=6) as dst:
        shutil.copyfileobj(src, dst)

    return output_path


def save_raw_selected_channels(
    signals: np.ndarray,
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)

    with output_path.open("wb") as f:
        f.write(signals.astype(np.int32, copy=False).tobytes())

    return output_path


def hdf5_selected_channels(
    signals: np.ndarray,
    meta: dict,
    output_path: str | Path,
) -> Path | None:
    try:
        import h5py
    except ImportError:
        return None

    output_path = Path(output_path)

    with h5py.File(output_path, "w") as f:
        f.create_dataset(
            "signals",
            data=signals.astype(np.int32, copy=False),
            compression="gzip",
            compression_opts=6,
            chunks=True,
        )
        f.attrs["sample_rate"] = meta["sample_rate"]
        f.attrs["channel_names"] = np.asarray(meta["channel_names"], dtype="S")

    return output_path


def build_compression_table(
    recording_path: str | Path,
    output_dir: str | Path,
    max_channels: int | None = None,
) -> dict:
    recording_path = Path(recording_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    signals, meta = read_edf_digital(recording_path, max_channels=max_channels)

    raw_selected = output_dir / f"{recording_path.stem}.selected_raw_i32"
    raw_selected_gz = output_dir / f"{recording_path.stem}.selected_raw_i32.gz"
    bsg = output_dir / f"{recording_path.stem}.bsg"
    h5 = output_dir / f"{recording_path.stem}.selected_channels.h5"

    save_raw_selected_channels(signals, raw_selected)
    gzip_file(raw_selected, raw_selected_gz)

    encode_biosig(
        signals,
        bsg,
        sample_rate=meta["sample_rate"],
        channel_names=meta["channel_names"],
        physical_dimensions=meta["physical_dimensions"],
        keyframe_interval=256,
        source=meta["source"],
    )

    h5_result = hdf5_selected_channels(signals, meta, h5)

    results = {
        "raw selected channels": file_size_mb(raw_selected),
        "gzip raw selected channels": file_size_mb(raw_selected_gz),
        "biosig": file_size_mb(bsg),
    }

    if h5_result is not None:
        results["HDF5 gzip selected channels"] = file_size_mb(h5_result)

    return results


def delta_distribution(
    recording_path: str | Path,
    max_channels: int | None = 8,
    max_samples: int = 2_000_000,
) -> np.ndarray:
    signals, _ = read_edf_digital(recording_path, max_channels=max_channels)

    if signals.shape[1] > max_samples:
        signals = signals[:, :max_samples]

    return np.diff(signals, axis=1).reshape(-1)


def benchmark_seek_latency(
    bsg_path: str | Path,
    windows: int = 50,
    seconds: float = 30.0,
) -> dict:
    rng = np.random.default_rng(0)

    with BiosigReader(bsg_path) as reader:
        sr = reader.header.sample_rate
        window_samples = max(1, int(seconds * sr))
        max_start = max(1, reader.header.samples - window_samples - 1)

        starts = rng.integers(0, max_start, size=windows)

        t0 = time.perf_counter()

        for s in starts:
            reader.read_window(0, int(s), int(s) + window_samples)

        biosig_time = (time.perf_counter() - t0) / windows

    return {"biosig window read": biosig_time}