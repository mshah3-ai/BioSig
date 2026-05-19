import subprocess
import sys

import numpy as np

from biosig.core import encode_biosig


def test_cli_info(tmp_path):
    data = np.arange(1000, dtype=np.int32).reshape(1, 1000)
    path = tmp_path / "cli.bsg"
    encode_biosig(data, path, sample_rate=100)

    result = subprocess.run(
        [sys.executable, "-m", "biosig.cli", "info", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Channels: 1" in result.stdout
    assert "Sample rate: 100" in result.stdout
