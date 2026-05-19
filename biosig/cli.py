from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .convert import convert_edf_to_bsg
from .core import BiosigReader
from .edf import find_recording
from .metrics import build_compression_table, benchmark_seek_latency, delta_distribution
from .plotting import (
    save_compression_plot,
    save_core_encoding_insight,
    save_delta_distribution_plot,
    save_seek_latency_plot,
    save_signal_preview,
)


def cmd_convert(args) -> None:
    out = convert_edf_to_bsg(
        args.input,
        args.output,
        keyframe_interval=args.keyframe_interval,
        max_channels=args.max_channels,
    )
    print(f"Wrote {out}")


def cmd_info(args) -> None:
    with BiosigReader(args.file) as reader:
        h = reader.header
        duration = h.samples / h.sample_rate
        size_mb = Path(args.file).stat().st_size / (1024 * 1024)

        print(f"File: {args.file}")
        print(f"Channels: {h.channels}")
        print(f"Samples: {h.samples}")
        print(f"Sample rate: {h.sample_rate:g} Hz")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Keyframe interval: {h.keyframe_interval}")
        print(f"Size: {size_mb:.2f} MB")
        print("Channel names:")
        for i, name in enumerate(h.channel_names):
            print(f"  {i}: {name}")


def cmd_slice(args) -> None:
    with BiosigReader(args.file) as reader:
        data = reader.read_seconds(args.channel, args.start, args.end)

    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sample_index", "value"])
            for i, v in enumerate(data):
                writer.writerow([i, int(v)])
        print(f"Wrote {args.output}")
    else:
        for v in data:
            print(int(v))


def cmd_bench(args) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    recording = Path(args.recording) if args.recording else find_recording(args.data_dir)
    bsg = output_dir / f"{recording.stem}.bsg"

    sizes = build_compression_table(recording, output_dir, max_channels=args.max_channels)
    save_compression_plot(sizes, output_dir / "compression_comparison.png")

    deltas = delta_distribution(recording, max_channels=args.max_channels)
    save_delta_distribution_plot(deltas, output_dir / "delta_distribution.png")

    if not bsg.exists():
        convert_edf_to_bsg(recording, bsg, max_channels=args.max_channels)

    latency = benchmark_seek_latency(bsg, windows=args.windows, seconds=args.window_seconds)
    save_seek_latency_plot(latency, output_dir / "seek_latency.png")

    with BiosigReader(bsg) as reader:
        signal = reader.read_seconds(0, 0, args.preview_seconds)
        save_signal_preview(signal, reader.header.sample_rate, output_dir / "signal_preview.png", seconds=args.preview_seconds)

    save_core_encoding_insight(output_dir / "core_encoding_insight.png")

    csv_path = output_dir / "comparison.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["method", "size_mb"])
        for k, v in sizes.items():
            writer.writerow([k, v])

    print(f"Recording: {recording}")
    print(f"Wrote figures and CSV to {output_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="biosig")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("convert")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--keyframe-interval", type=int, default=256)
    p.add_argument("--max-channels", type=int)
    p.set_defaults(func=cmd_convert)

    p = sub.add_parser("info")
    p.add_argument("file")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("slice")
    p.add_argument("file")
    p.add_argument("--channel", required=True)
    p.add_argument("--start", type=float, required=True)
    p.add_argument("--end", type=float, required=True)
    p.add_argument("--output")
    p.set_defaults(func=cmd_slice)

    p = sub.add_parser("bench")
    p.add_argument("data_dir")
    p.add_argument("--recording")
    p.add_argument("--output-dir", default="figures")
    p.add_argument("--max-channels", type=int)
    p.add_argument("--windows", type=int, default=50)
    p.add_argument("--window-seconds", type=float, default=30.0)
    p.add_argument("--preview-seconds", type=float, default=20.0)
    p.set_defaults(func=cmd_bench)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
