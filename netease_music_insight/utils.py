import json
import os
import re
import time
from pathlib import Path


def safe_name(value: str, fallback: str = "netease_user") -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", str(value)).strip(" .")
    if name.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        name = f"_{name}"
    return name[:80].rstrip(" .") or fallback


def atomic_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _replace(tmp, path)


def atomic_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    _replace(tmp, path)


def _replace(tmp: Path, path: Path) -> None:
    """Windows scanners can briefly hold a newly written file open."""
    for attempt in range(6):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if os.name != "nt" or attempt == 5:
                raise
            time.sleep(0.05 * 2 ** attempt)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
