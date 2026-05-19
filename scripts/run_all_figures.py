from __future__ import annotations

import argparse
import csv
from pathlib import Path

from biosig.convert import convert_edf_to_bsg
from biosig.core import BiosigReader
from biosig.edf import find_recording
from biosig.metrics import build_compression_table, benchmark_seek_latency, delta_distribution
from biosig.plotting import (
    save_compression_plot,
    save_core_encoding_insight,
    save_delta_distribution_plot,
    save_seek_latency_plot,
    save_signal_preview,
)


def main():
    parser = argparse.ArgumentParser(description="Run complete biosig benchmark and generate all figures.")
    parser.add_argument("data_dir", help="Folder containing Sleep-EDF .rec/.hyp or EDF files.")
    parser.add_argument("--recording", help="Specific .rec or .edf file. If omitted, the first recording is used.")
    parser.add_argument("--output-dir", default="figures")
    parser.add_argument("--max-channels", type=int, help="Optional channel limit for faster local testing.")
    parser.add_argument("--preview-seconds", type=float, default=20)
    parser.add_argument("--seek-windows", type=int, default=50)
    parser.add_argument("--seek-window-seconds", type=float, default=30)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    recording = Path(args.recording) if args.recording else find_recording(args.data_dir)
    bsg = output_dir / f"{recording.stem}.bsg"

    print(f"Using recording: {recording}")

    sizes = build_compression_table(recording, output_dir, max_channels=args.max_channels)
    save_compression_plot(sizes, output_dir / "compression_comparison.png")

    deltas = delta_distribution(recording, max_channels=args.max_channels)
    save_delta_distribution_plot(deltas, output_dir / "delta_distribution.png")

    if not bsg.exists():
        convert_edf_to_bsg(recording, bsg, max_channels=args.max_channels)

    latency = benchmark_seek_latency(
        bsg,
        windows=args.seek_windows,
        seconds=args.seek_window_seconds,
    )
    save_seek_latency_plot(latency, output_dir / "seek_latency.png")

    with BiosigReader(bsg) as reader:
        signal = reader.read_seconds(0, 0, args.preview_seconds)
        save_signal_preview(
            signal,
            reader.header.sample_rate,
            output_dir / "signal_preview.png",
            seconds=args.preview_seconds,
        )

    save_core_encoding_insight(output_dir / "core_encoding_insight.png")

    csv_path = output_dir / "comparison.csv"
    raw_size = sizes["raw selected channels"]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["method", "size_mb", "compression_ratio_vs_raw"])
        for method, size in sizes.items():
            writer.writerow([method, size, raw_size / size])

    print(f"Wrote {output_dir / 'compression_comparison.png'}")
    print(f"Wrote {output_dir / 'delta_distribution.png'}")
    print(f"Wrote {output_dir / 'seek_latency.png'}")
    print(f"Wrote {output_dir / 'signal_preview.png'}")
    print(f"Wrote {output_dir / 'core_encoding_insight.png'}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
