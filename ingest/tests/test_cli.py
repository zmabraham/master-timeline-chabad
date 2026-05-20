import subprocess
import sys
from pathlib import Path


def test_cli_lists_known_passes():
    result = subprocess.run(
        [sys.executable, "-m", "timeline_ingest", "--help"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0
    assert "pass1" in result.stdout
