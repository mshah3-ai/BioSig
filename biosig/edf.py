from __future__ import annotations

from pathlib import Path

import numpy as np
import pyedflib


def find_recording(folder: str | Path) -> Path:
    folder = Path(folder)

    candidates = sorted(folder.rglob("*.edf")) + sorted(folder.rglob("*.rec"))

    candidates = [
        p for p in candidates
        if "hyp" not in p.name.lower()
        and "hypnogram" not in p.name.lower()
        and p.stat().st_size > 1024
    ]

    if not candidates:
        raise FileNotFoundError(f"No EDF/REC recording found under {folder}")

    return candidates[0]


def matching_hypnogram(recording_path: str | Path) -> Path | None:
    recording_path = Path(recording_path)
    folder = recording_path.parent

    stem = recording_path.stem.lower()
    subject_prefix = stem[:6]

    candidates = sorted(folder.glob("*.hyp")) + sorted(folder.glob("*Hypnogram*.edf")) + sorted(folder.glob("*hyp*.edf"))

    for c in candidates:
        if subject_prefix and c.stem.lower().startswith(subject_prefix):
            return c

    return candidates[0] if candidates else None


def read_edf_digital(path: str | Path, max_channels: int | None = None) -> tuple[np.ndarray, dict]:
    path = Path(path)
    reader = pyedflib.EdfReader(str(path))

    try:
        n_channels = reader.signals_in_file
        if max_channels is not None:
            n_channels = min(n_channels, max_channels)

        sample_rates = [float(reader.getSampleFrequency(i)) for i in range(n_channels)]
        first_rate = sample_rates[0]

        if any(abs(sr - first_rate) > 1e-9 for sr in sample_rates):
            raise ValueError(
                "This MVP expects selected channels to share one sample rate. "
                "Pass --max-channels to choose compatible channels or resample before conversion."
            )

        signals = []
        names = []
        dims = []

        for i in range(n_channels):
            try:
                sig = reader.readSignal(i, digital=True)
            except TypeError:
                sig = reader.readSignal(i)
                sig = np.rint(sig).astype(np.int32)

            signals.append(np.asarray(sig, dtype=np.int32))
            names.append(reader.getLabel(i).strip() or f"ch{i}")
            dims.append(reader.getPhysicalDimension(i).strip())

        min_len = min(len(s) for s in signals)
        signals = np.vstack([s[:min_len] for s in signals])

        meta = {
            "sample_rate": first_rate,
            "channel_names": names,
            "physical_dimensions": dims,
            "source": str(path),
        }

        return signals, meta
    finally:
        reader.close()
