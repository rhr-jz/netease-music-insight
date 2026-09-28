"""Small platform integrations used by the command-line application."""
import os
import subprocess
import sys
from pathlib import Path


def open_path(path: Path) -> bool:
    """Open a file or folder with the platform's default application."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform in {"darwin", "linux"}:
            command = "open" if sys.platform == "darwin" else "xdg-open"
            result = subprocess.run(
                [command, str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return result.returncode == 0
        else:
            return False
    except OSError:
        return False
    return True
