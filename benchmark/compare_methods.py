from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from biosig.edf import find_recording
from biosig.metrics import build_compression_table


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir")
    parser.add_argument("--recording")
    parser.add_argument("--output-dir", default="figures")
    parser.add_argument("--max-channels", type=int)
    args = parser.parse_args()

    recording = Path(args.recording) if args.recording else find_recording(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sizes = build_compression_table(recording, output_dir, max_channels=args.max_channels)
    baseline = sizes["EDF/REC"]

    df = pd.DataFrame({
        "method": list(sizes.keys()),
        "size_mb": list(sizes.values()),
    })
    df["compression_ratio_vs_raw"] = baseline / df["size_mb"]

    out = output_dir / "comparison.csv"
    df.to_csv(out, index=False)

    print(df.to_string(index=False))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
