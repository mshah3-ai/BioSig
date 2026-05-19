from __future__ import annotations

import argparse
from pathlib import Path

from biosig.plotting import save_core_encoding_insight


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="figures")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    out = save_core_encoding_insight(output_dir / "core_encoding_insight.png")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
