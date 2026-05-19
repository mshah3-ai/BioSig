from __future__ import annotations

from pathlib import Path

import numpy as np


def save_compression_plot(sizes: dict, output_path: str | Path) -> Path:
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    labels = list(sizes.keys())
    values = [sizes[k] for k in labels]

    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values)
    plt.ylabel("File size (MB)")
    plt.title("Storage comparison")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()

    return output_path


def save_delta_distribution_plot(deltas, output_path: str | Path) -> Path:
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    deltas = np.asarray(deltas)

    if deltas.size > 500_000:
        rng = np.random.default_rng(0)
        deltas = rng.choice(deltas, size=500_000, replace=False)

    plt.figure(figsize=(8, 4.5))
    plt.hist(deltas, bins=150)
    plt.xlabel("Inter-sample delta")
    plt.ylabel("Count")
    plt.title("Most biosignal samples change by small deltas")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()

    return output_path


def save_seek_latency_plot(metrics: dict, output_path: str | Path) -> Path:
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    labels = list(metrics.keys())
    values = [metrics[k] for k in labels]

    plt.figure(figsize=(7, 4))
    plt.bar(labels, values)
    plt.ylabel("Seconds per window")
    plt.title("Random window read latency")
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()

    return output_path


def save_signal_preview(signal, sample_rate: float, output_path: str | Path, seconds: float = 20.0) -> Path:
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    n = min(len(signal), int(seconds * sample_rate))
    x = np.arange(n) / sample_rate

    plt.figure(figsize=(10, 3.5))
    plt.plot(x, signal[:n], linewidth=0.8)
    plt.xlabel("Time (s)")
    plt.ylabel("Digital amplitude")
    plt.title("Decoded biosig signal preview")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()

    return output_path


def save_core_encoding_insight(output_path: str | Path) -> Path:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    output_path = Path(output_path)

    raw = [4821, 4823, 4820, 4826, 4822, 4819, 4824, 4821, 4825]
    deltas = [raw[0]] + [raw[i] - raw[i - 1] for i in range(1, len(raw))]

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7)
    ax.axis("off")

    ax.text(0.2, 6.5, "EDF format — stores every raw value", fontsize=14, weight="bold")

    for i, val in enumerate(raw):
        ax.add_patch(Rectangle((0.2 + i * 1.05, 5.3), 0.85, 0.6, fill=False))
        ax.text(0.625 + i * 1.05, 5.65, str(val), ha="center", va="center", fontsize=10)
        ax.text(0.625 + i * 1.05, 5.42, f"sample {i}", ha="center", va="center", fontsize=8)

    ax.text(0.2, 4.9, "Each sample is stored as a full integer.", fontsize=10)
    ax.annotate("biosig transform", xy=(5.1, 4.1), xytext=(5.1, 4.65), arrowprops=dict(arrowstyle="->"))

    ax.text(0.2, 3.4, "biosig format — stores keyframes + deltas", fontsize=14, weight="bold")

    for i, val in enumerate(deltas):
        ax.add_patch(Rectangle((0.2 + i * 1.05, 2.2), 0.85, 0.6, fill=False))
        label = str(val) if i == 0 else f"{val:+d}"
        ax.text(0.625 + i * 1.05, 2.55, label, ha="center", va="center", fontsize=10)
        if i == 0:
            ax.text(0.625 + i * 1.05, 2.32, "keyframe", ha="center", va="center", fontsize=8)
        else:
            ax.text(0.625 + i * 1.05, 2.32, "delta", ha="center", va="center", fontsize=8)

    ax.text(0.2, 1.75, "Small deltas fit in 1 byte. Periodic keyframes make random access possible.", fontsize=10)
    ax.text(0.2, 1.15, "Storage comparison example", fontsize=12, weight="bold")
    ax.add_patch(Rectangle((0.2, 0.65), 8.7, 0.25))
    ax.text(9.1, 0.77, "EDF: large", va="center", fontsize=10)
    ax.add_patch(Rectangle((0.2, 0.25), 1.2, 0.25))
    ax.text(1.55, 0.37, "biosig: smaller", va="center", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()

    return output_path
