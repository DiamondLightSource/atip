import subprocess
import sys

from atip import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "atip", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
