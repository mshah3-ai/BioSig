from __future__ import annotations

import argparse
from pathlib import Path

from biosig.edf import find_recording
from biosig.metrics import build_compression_table
from biosig.plotting import save_compression_plot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir")
    parser.add_argument("--recording")
    parser.add_argument("--output-dir", default="figures")
    parser.add_argument("--max-channels", type=int)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    recording = Path(args.recording) if args.recording else find_recording(args.data_dir)
    sizes = build_compression_table(recording, output_dir, max_channels=args.max_channels)
    out = save_compression_plot(sizes, output_dir / "compression_comparison.png")

    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
