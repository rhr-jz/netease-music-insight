"""Build an allowlisted static site; no workspace exports or credentials are copied."""
import argparse
import hashlib
import json
import shutil
import sys
import tarfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from netease_music_insight import __version__
from netease_music_insight.report import build_data

RUNTIME_VERSION = "314.0.7"
RUNTIME_SHA256 = "2abdcc2e35208af406e07724cffa85bc582ced97e9028383ecf5462541393f95"
RUNTIME_URL = f"https://github.com/pyodide/pyodide/releases/download/{RUNTIME_VERSION}/pyodide-core-{RUNTIME_VERSION}.tar.bz2"
RUNTIME_FILES = {"pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "pyodide-lock.json", "python_stdlib.zip"}
CORE_FILES = ["__init__.py", "utils.py", "guidance.py", "report.py", "combined.py", "browser.py",
              "desktop/__init__.py", "desktop/library.py"]
STATIC_FILES = ["index.html", "styles.css", "app.js", "worker.js", "sw.js", "favicon.svg"]


def demo(provider):
    artists = ["演示歌手 A", "演示歌手 B", "演示歌手 C", "演示歌手 D"]
    tracks = [{"id": str(index + 1), "name": f"演示歌曲 {index + 1:02d}",
               "artists": artists[(index // 4) % len(artists)], "album": f"演示专辑 {index // 7 + 1}",
               "provider": provider, "duration_ms": 180_000 + index * 1_000,
               "liked_at": f"2025-{index % 12 + 1:02d}-05T10:00:00+08:00" if provider == "netease" else None}
              for index in range(36 if provider == "netease" else 24)]
    playlists = [{"id": str(index + 101), "name": f"演示歌单 {index + 1}",
                  "created_by_user": index % 2 == 0, "tracks": tracks[index:index + 12], "track_count": 12,
                  "created_at": "2025-04-02T09:00:00+08:00", "subscribed_at": None}
                 for index in range(6 if provider == "netease" else 4)]
    data = build_data({"userId": "demo", "nickname": "演示用户"}, tracks, playlists, [], provider=provider)
    data["export_meta"]["exported_at"] = "2026-09-30T10:00:00+08:00"
    return data


def build():
    cache = ROOT / "build/browser/pyodide-core.tar.bz2"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists():
        with urlopen(RUNTIME_URL, timeout=90) as response, cache.open("wb") as target:
            shutil.copyfileobj(response, target)
    if hashlib.sha256(cache.read_bytes()).hexdigest() != RUNTIME_SHA256:
        raise RuntimeError("Pyodide archive integrity verification failed")
    out = ROOT / "_site"
    # Only this named build output may ever be removed, and no symlinks followed.
    if out.is_symlink() or out.resolve() != ROOT.resolve() / "_site":
        raise RuntimeError("Unsafe build output path")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    for name in STATIC_FILES:
        shutil.copyfile(ROOT / "browser" / name, out / name)
    (out / "licenses").mkdir()
    for name in ("PYODIDE.txt", "PYTHON.txt"):
        shutil.copyfile(ROOT / "browser/licenses" / name, out / "licenses" / name)
    runtime = out / "runtime"
    runtime.mkdir()
    with tarfile.open(cache) as archive:
        for name in sorted(RUNTIME_FILES):
            member = archive.getmember("pyodide/" + name)
            if not member.isfile():
                raise RuntimeError("Unexpected runtime archive member")
            with archive.extractfile(member) as source, (runtime / name).open("wb") as target:
                shutil.copyfileobj(source, target)
    files = {}
    for name in CORE_FILES:
        files[name] = (ROOT / "netease_music_insight" / name).read_text(encoding="utf-8")
    (out / "core.json").write_text(json.dumps(files, ensure_ascii=False), encoding="utf-8")
    (out / "demo.json").write_text(json.dumps([demo("netease"), demo("qq_music")], ensure_ascii=False), encoding="utf-8")
    shutil.copyfile(ROOT / "LICENSE", out / "LICENSE.txt")
    (out / "THIRD_PARTY.txt").write_text(
        f"Music Insight {__version__}: GPL-3.0-or-later.\n"
        f"Pyodide {RUNTIME_VERSION}: Mozilla Public License 2.0.\n"
        "https://github.com/pyodide/pyodide/blob/314.0.7/LICENSE\n"
        "Full Pyodide license: licenses/PYODIDE.txt.\n"
        "Python 3.14.2: Python Software Foundation License; full text: licenses/PYTHON.txt.\n"
        "The original Node and QQ API dependencies are not included in this static site.\n", encoding="utf-8")
    (out / ".nojekyll").touch()
    manifest = sorted(path.relative_to(out).as_posix() for path in out.rglob("*") if path.is_file())
    fingerprint = hashlib.sha256(b"".join((out / name).read_bytes() for name in manifest)).hexdigest()[:16]
    (out / "sw.js").write_text((out / "sw.js").read_text(encoding="utf-8").replace("__BUILD_ID__", fingerprint), encoding="utf-8")
    (out / "precache.json").write_text(json.dumps({"version": fingerprint, "files": manifest}), encoding="utf-8")
    print(f"Browser site built: {len(manifest)} files, {sum(p.stat().st_size for p in out.rglob('*') if p.is_file()):,} bytes")


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
