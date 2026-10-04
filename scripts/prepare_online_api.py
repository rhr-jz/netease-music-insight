"""Build-time dependency preparation. Never called by user jobs."""
import argparse
import hashlib
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from netease_music_insight.bootstrap import _unzip_safe

COMMIT = 'b027aca40abbf3409bb8feb4840df732b7b70825'
URL = f'https://codeload.github.com/TH911/NeteaseCloudMusicApi/zip/{COMMIT}'
SHA256 = 'bb311e73ddcad40148b5e15ca26cabacd2b499af91af097388c344a959740640'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    parser.add_argument('--download-only', action='store_true')
    args = parser.parse_args()
    target = args.destination.resolve()
    if target.exists():
        raise SystemExit('Use a new empty destination, not an existing directory')
    with tempfile.TemporaryDirectory() as temp:
        archive = Path(temp)/'api.zip'
        request = urllib.request.Request(URL,headers={'User-Agent':'MusicInsight-build/3'})
        with urllib.request.urlopen(request,timeout=120) as source,archive.open('wb') as out:
            shutil.copyfileobj(source,out)
        print('Pinned NetEase source:', COMMIT)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != SHA256:
            raise SystemExit('Upstream source checksum mismatch')
        print('Archive SHA256:', digest)
        unpack = Path(temp)/'source'
        _unzip_safe(archive,unpack)
        folders = list(unpack.glob('*/package.json'))
        if len(folders)!=1:
            raise SystemExit('Invalid pinned source archive')
        shutil.copytree(folders[0].parent,target)
        lock = Path(__file__).resolve().parents[1]/'deploy/netease-package-lock.json'
        shutil.copyfile(lock,target/'package-lock.json')
    if not args.download_only:
        npm = shutil.which('npm.cmd') or shutil.which('npm')
        if not npm:
            raise SystemExit('Node/npm is required during build')
        subprocess.run([npm,'ci','--omit=dev','--ignore-scripts','--no-audit','--no-fund'],cwd=target,check=True,timeout=600)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
