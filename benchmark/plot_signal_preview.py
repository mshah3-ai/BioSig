from __future__ import annotations

import argparse
from pathlib import Path

from biosig.convert import convert_edf_to_bsg
from biosig.core import BiosigReader
from biosig.edf import find_recording
from biosig.plotting import save_signal_preview


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir")
    parser.add_argument("--recording")
    parser.add_argument("--output-dir", default="figures")
    parser.add_argument("--max-channels", type=int)
    parser.add_argument("--seconds", type=float, default=20)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    recording = Path(args.recording) if args.recording else find_recording(args.data_dir)
    bsg = output_dir / f"{recording.stem}.bsg"

    if not bsg.exists():
        convert_edf_to_bsg(recording, bsg, max_channels=args.max_channels)

    with BiosigReader(bsg) as reader:
        signal = reader.read_seconds(0, 0, args.seconds)
        out = save_signal_preview(signal, reader.header.sample_rate, output_dir / "signal_preview.png", seconds=args.seconds)

    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
