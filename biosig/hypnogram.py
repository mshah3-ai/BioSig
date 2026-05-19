from __future__ import annotations

from pathlib import Path

import pyedflib


def read_annotations(path: str | Path):
    reader = pyedflib.EdfReader(str(path))
    try:
        onset, duration, description = reader.readAnnotations()
        return list(zip(onset, duration, description))
    finally:
        reader.close()


def normalize_stage(label: str) -> str:
    s = str(label).lower()

    if "wake" in s or s == "w":
        return "Wake"
    if "rem" in s:
        return "REM"
    if "1" in s:
        return "N1"
    if "2" in s:
        return "N2"
    if "3" in s or "4" in s:
        return "N3"
    if "movement" in s or "mt" in s:
        return "Movement"

    return str(label)
