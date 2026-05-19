from __future__ import annotations

import argparse
from pathlib import Path

from biosig.convert import convert_edf_to_bsg
from biosig.edf import find_recording
from biosig.metrics import benchmark_seek_latency
from biosig.plotting import save_seek_latency_plot


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
    bsg = output_dir / f"{recording.stem}.bsg"

    if not bsg.exists():
        convert_edf_to_bsg(recording, bsg, max_channels=args.max_channels)

    metrics = benchmark_seek_latency(bsg)
    out = save_seek_latency_plot(metrics, output_dir / "seek_latency.png")

    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
