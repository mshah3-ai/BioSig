from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

MAGIC = b"BSG4"

HEADER_LEN_STRUCT = struct.Struct("<Q")
CHANNEL_HEADER_STRUCT = struct.Struct("<QQ")
OFFSET_STRUCT = struct.Struct("<Q")
KEYFRAME_STRUCT = struct.Struct("<i")
BLOCK_HEADER_STRUCT = struct.Struct("<BIB")

BLOCK_RAW_INT8 = 1
BLOCK_RAW_INT16 = 2
BLOCK_RAW_INT32 = 4
BLOCK_BITPACKED = 8


@dataclass
class BiosigHeader:
    sample_rate: float
    channels: int
    samples: int
    channel_names: list[str]
    physical_dimensions: list[str]
    keyframe_interval: int
    dtype: str
    source: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "BiosigHeader":
        return cls(
            sample_rate=float(d["sample_rate"]),
            channels=int(d["channels"]),
            samples=int(d["samples"]),
            channel_names=list(
                d.get("channel_names", [f"ch{i}" for i in range(int(d["channels"]))])
            ),
            physical_dimensions=list(
                d.get("physical_dimensions", [""] * int(d["channels"]))
            ),
            keyframe_interval=int(d["keyframe_interval"]),
            dtype=str(d.get("dtype", "int32")),
            source=d.get("source"),
        )

    def to_dict(self) -> dict:
        return {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "samples": self.samples,
            "channel_names": self.channel_names,
            "physical_dimensions": self.physical_dimensions,
            "keyframe_interval": self.keyframe_interval,
            "dtype": self.dtype,
            "source": self.source,
        }


def _bits_needed_for_signed(min_value: int, max_value: int) -> int:
    for bits in range(1, 32):
        low = -(1 << (bits - 1))
        high = (1 << (bits - 1)) - 1
        if low <= min_value and max_value <= high:
            return bits
    return 32


def _pack_signed(values: np.ndarray, bits: int) -> bytes:
    if values.size == 0:
        return b""

    mask = (1 << bits) - 1
    out = bytearray()
    buffer = 0
    used = 0

    for value in values.astype(np.int64, copy=False):
        encoded = int(value) & mask
        buffer |= encoded << used
        used += bits

        while used >= 8:
            out.append(buffer & 0xFF)
            buffer >>= 8
            used -= 8

    if used:
        out.append(buffer & 0xFF)

    return bytes(out)


def _unpack_signed(raw: bytes, count: int, bits: int) -> np.ndarray:
    if count == 0:
        return np.array([], dtype=np.int32)

    mask = (1 << bits) - 1
    sign_bit = 1 << (bits - 1)
    out = np.empty(count, dtype=np.int32)

    buffer = 0
    used = 0
    idx = 0
    byte_idx = 0

    while idx < count:
        while used < bits:
            if byte_idx >= len(raw):
                raise ValueError("Corrupt biosig block: incomplete bit-packed payload")
            buffer |= raw[byte_idx] << used
            used += 8
            byte_idx += 1

        encoded = buffer & mask
        buffer >>= bits
        used -= bits

        if encoded & sign_bit:
            encoded -= 1 << bits

        out[idx] = encoded
        idx += 1

    return out


def _encode_block(first_value: int, deltas: np.ndarray) -> bytes:
    blob = bytearray()
    blob += KEYFRAME_STRUCT.pack(int(first_value))

    if deltas.size == 0:
        blob += BLOCK_HEADER_STRUCT.pack(BLOCK_RAW_INT8, 0, 8)
        return bytes(blob)

    deltas = deltas.astype(np.int32, copy=False)

    min_delta = int(deltas.min())
    max_delta = int(deltas.max())
    bits = _bits_needed_for_signed(min_delta, max_delta)

    if bits < 8:
        packed = _pack_signed(deltas, bits)
        blob += BLOCK_HEADER_STRUCT.pack(BLOCK_BITPACKED, int(deltas.size), bits)
        blob += packed
        return bytes(blob)

    if bits == 8:
        packed = deltas.astype(np.int8, copy=False).tobytes()
        blob += BLOCK_HEADER_STRUCT.pack(BLOCK_RAW_INT8, int(deltas.size), 8)
        blob += packed
        return bytes(blob)

    if bits <= 16:
        packed = deltas.astype("<i2", copy=False).tobytes()
        blob += BLOCK_HEADER_STRUCT.pack(BLOCK_RAW_INT16, int(deltas.size), 16)
        blob += packed
        return bytes(blob)

    packed = deltas.astype("<i4", copy=False).tobytes()
    blob += BLOCK_HEADER_STRUCT.pack(BLOCK_RAW_INT32, int(deltas.size), 32)
    blob += packed
    return bytes(blob)


def _decode_block(f) -> np.ndarray:
    first_raw = f.read(KEYFRAME_STRUCT.size)

    if len(first_raw) != KEYFRAME_STRUCT.size:
        raise ValueError("Corrupt biosig block: missing keyframe")

    first = KEYFRAME_STRUCT.unpack(first_raw)[0]

    header_raw = f.read(BLOCK_HEADER_STRUCT.size)

    if len(header_raw) != BLOCK_HEADER_STRUCT.size:
        raise ValueError("Corrupt biosig block: missing block header")

    block_type, n_deltas, bits = BLOCK_HEADER_STRUCT.unpack(header_raw)

    if block_type == BLOCK_BITPACKED:
        n_bytes = (n_deltas * bits + 7) // 8
        raw = f.read(n_bytes)

        if len(raw) != n_bytes:
            raise ValueError("Corrupt biosig block: incomplete bit-packed payload")

        deltas = _unpack_signed(raw, n_deltas, bits)

    elif block_type == BLOCK_RAW_INT8:
        raw = f.read(n_deltas)

        if len(raw) != n_deltas:
            raise ValueError("Corrupt biosig block: incomplete int8 payload")

        deltas = np.frombuffer(raw, dtype=np.int8).astype(np.int32)

    elif block_type == BLOCK_RAW_INT16:
        raw = f.read(n_deltas * 2)

        if len(raw) != n_deltas * 2:
            raise ValueError("Corrupt biosig block: incomplete int16 payload")

        deltas = np.frombuffer(raw, dtype="<i2").astype(np.int32)

    elif block_type == BLOCK_RAW_INT32:
        raw = f.read(n_deltas * 4)

        if len(raw) != n_deltas * 4:
            raise ValueError("Corrupt biosig block: incomplete int32 payload")

        deltas = np.frombuffer(raw, dtype="<i4").astype(np.int32)

    else:
        raise ValueError(f"Corrupt biosig block: unknown block type {block_type}")

    values = np.empty(n_deltas + 1, dtype=np.int32)
    values[0] = first

    if n_deltas:
        values[1:] = first + np.cumsum(deltas, dtype=np.int32)

    return values


def encode_biosig(
    signals: np.ndarray,
    out_path: str | Path,
    sample_rate: float,
    channel_names: Sequence[str] | None = None,
    physical_dimensions: Sequence[str] | None = None,
    keyframe_interval: int = 256,
    source: str | None = None,
) -> Path:
    arr = np.asarray(signals)

    if arr.ndim != 2:
        raise ValueError("signals must have shape (channels, samples)")

    if not np.issubdtype(arr.dtype, np.integer):
        arr = np.rint(arr).astype(np.int32)
    else:
        arr = arr.astype(np.int32, copy=False)

    channels, samples = arr.shape

    if samples == 0:
        raise ValueError("signals must contain at least one sample")

    if keyframe_interval < 2:
        raise ValueError("keyframe_interval must be at least 2")

    if channel_names is None:
        channel_names = [f"ch{i}" for i in range(channels)]

    if physical_dimensions is None:
        physical_dimensions = [""] * channels

    if len(channel_names) != channels:
        raise ValueError("channel_names length must match number of channels")

    header = BiosigHeader(
        sample_rate=float(sample_rate),
        channels=channels,
        samples=samples,
        channel_names=list(channel_names),
        physical_dimensions=list(physical_dimensions),
        keyframe_interval=int(keyframe_interval),
        dtype="int32",
        source=source,
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    channel_blobs: list[bytes] = []
    channel_indexes: list[list[int]] = []

    for c in range(channels):
        channel = arr[c]
        blob = bytearray()
        offsets: list[int] = []

        for start in range(0, samples, keyframe_interval):
            stop = min(start + keyframe_interval, samples)
            offsets.append(len(blob))

            block = channel[start:stop]
            first = int(block[0])
            deltas = np.diff(block).astype(np.int32)

            blob += _encode_block(first, deltas)

        channel_blobs.append(bytes(blob))
        channel_indexes.append(offsets)

    header_bytes = json.dumps(header.to_dict(), separators=(",", ":")).encode("utf-8")

    with out_path.open("wb") as f:
        f.write(MAGIC)
        f.write(HEADER_LEN_STRUCT.pack(len(header_bytes)))
        f.write(header_bytes)

        f.write(struct.pack("<Q", channels))

        for blob, offsets in zip(channel_blobs, channel_indexes):
            f.write(CHANNEL_HEADER_STRUCT.pack(len(offsets), len(blob)))

            for off in offsets:
                f.write(OFFSET_STRUCT.pack(off))

            f.write(blob)

    return out_path


class BiosigReader:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._f = self.path.open("rb")
        self.header: BiosigHeader
        self._channel_data_starts: list[int] = []
        self._channel_indexes: list[list[int]] = []
        self._channel_blob_sizes: list[int] = []
        self._parse()

    def _parse(self) -> None:
        f = self._f
        f.seek(0)

        magic = f.read(4)

        if magic != MAGIC:
            raise ValueError(
                "Invalid biosig file. This reader expects BSG4 files. "
                "Delete old .bsg files and reconvert."
            )

        header_len = HEADER_LEN_STRUCT.unpack(f.read(8))[0]
        header = json.loads(f.read(header_len).decode("utf-8"))
        self.header = BiosigHeader.from_dict(header)

        channels_in_file = struct.unpack("<Q", f.read(8))[0]

        if channels_in_file != self.header.channels:
            raise ValueError("Header channel count does not match stream")

        for _ in range(self.header.channels):
            n_keyframes, blob_size = CHANNEL_HEADER_STRUCT.unpack(
                f.read(CHANNEL_HEADER_STRUCT.size)
            )

            offsets = [
                OFFSET_STRUCT.unpack(f.read(OFFSET_STRUCT.size))[0]
                for _ in range(n_keyframes)
            ]

            data_start = f.tell()

            self._channel_indexes.append(offsets)
            self._channel_data_starts.append(data_start)
            self._channel_blob_sizes.append(blob_size)

            f.seek(blob_size, 1)

    def close(self) -> None:
        self._f.close()

    def __enter__(self) -> "BiosigReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def read(self, channels: int | str | Iterable[int | str] | None = None) -> np.ndarray:
        selected = self._normalize_channels(channels)
        data = [self.read_window(ch, 0, self.header.samples) for ch in selected]
        return np.vstack(data)

    def read_window(
        self,
        channel: int | str,
        start_sample: int,
        stop_sample: int,
    ) -> np.ndarray:
        ch = self._channel_to_index(channel)

        start_sample = max(0, int(start_sample))
        stop_sample = min(self.header.samples, int(stop_sample))

        if stop_sample <= start_sample:
            return np.array([], dtype=np.int32)

        pieces = []
        pos = start_sample

        while pos < stop_sample:
            block_id = pos // self.header.keyframe_interval
            block_start = block_id * self.header.keyframe_interval
            block_stop = min(
                block_start + self.header.keyframe_interval,
                self.header.samples,
            )

            f = self._f
            f.seek(self._channel_data_starts[ch] + self._channel_indexes[ch][block_id])

            block_values = _decode_block(f)

            local_start = max(pos, block_start) - block_start
            local_stop = min(stop_sample, block_stop) - block_start

            pieces.append(block_values[local_start:local_stop])

            pos = block_stop

        if not pieces:
            return np.array([], dtype=np.int32)

        return np.concatenate(pieces).astype(np.int32, copy=False)

    def read_seconds(self, channel: int | str, start: float, end: float) -> np.ndarray:
        sr = self.header.sample_rate
        return self.read_window(channel, int(start * sr), int(end * sr))

    def _channel_to_index(self, channel: int | str) -> int:
        if isinstance(channel, str):
            if channel not in self.header.channel_names:
                raise ValueError(f"Unknown channel name: {channel}")
            return self.header.channel_names.index(channel)

        channel = int(channel)

        if not 0 <= channel < self.header.channels:
            raise IndexError("channel out of range")

        return channel

    def _normalize_channels(self, channels):
        if channels is None:
            return list(range(self.header.channels))

        if isinstance(channels, (int, str)):
            return [self._channel_to_index(channels)]

        return [self._channel_to_index(c) for c in channels]


def read_biosig(path: str | Path) -> tuple[dict, np.ndarray]:
    with BiosigReader(path) as reader:
        return reader.header.to_dict(), reader.read()


def read_biosig_window(
    path: str | Path,
    channel: int | str,
    start_sample: int,
    stop_sample: int,
) -> tuple[dict, np.ndarray]:
    with BiosigReader(path) as reader:
        return reader.header.to_dict(), reader.read_window(
            channel,
            start_sample,
            stop_sample,
        )
