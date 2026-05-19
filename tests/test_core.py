import numpy as np

from biosig.core import BiosigReader, encode_biosig, read_biosig


def test_roundtrip(tmp_path):
    rng = np.random.default_rng(0)
    deltas = rng.integers(-5, 6, size=(3, 2000))
    data = np.cumsum(deltas, axis=1).astype(np.int32)

    path = tmp_path / "sample.bsg"
    encode_biosig(data, path, sample_rate=100, channel_names=["a", "b", "c"])

    header, decoded = read_biosig(path)

    assert header["channels"] == 3
    assert decoded.dtype == np.int32
    np.testing.assert_array_equal(data, decoded)


def test_window_read_matches_full_read(tmp_path):
    rng = np.random.default_rng(1)
    data = np.cumsum(rng.integers(-3, 4, size=(2, 1500)), axis=1).astype(np.int32)

    path = tmp_path / "window.bsg"
    encode_biosig(data, path, sample_rate=100, keyframe_interval=128)

    with BiosigReader(path) as reader:
        window = reader.read_window(1, 257, 999)

    np.testing.assert_array_equal(window, data[1, 257:999])


def test_channel_name_read(tmp_path):
    data = np.vstack([
        np.arange(1000),
        np.arange(1000) * 2,
    ]).astype(np.int32)

    path = tmp_path / "names.bsg"
    encode_biosig(data, path, sample_rate=100, channel_names=["Fpz", "Cz"])

    with BiosigReader(path) as reader:
        out = reader.read_window("Cz", 10, 20)

    np.testing.assert_array_equal(out, data[1, 10:20])
