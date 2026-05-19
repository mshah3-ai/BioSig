from __future__ import annotations

from pathlib import Path

from .core import encode_biosig
from .edf import read_edf_digital


def convert_edf_to_bsg(
    input_path: str | Path,
    output_path: str | Path,
    keyframe_interval: int = 256,
    max_channels: int | None = None,
) -> Path:
    signals, meta = read_edf_digital(input_path, max_channels=max_channels)

    return encode_biosig(
        signals,
        output_path,
        sample_rate=meta["sample_rate"],
        channel_names=meta["channel_names"],
        physical_dimensions=meta["physical_dimensions"],
        keyframe_interval=keyframe_interval,
        source=meta["source"],
    )
