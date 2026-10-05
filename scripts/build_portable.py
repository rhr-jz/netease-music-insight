"""Build a self-contained native desktop + Local Web package on its target OS.

Only Python, the system WebView, Node and production API dependencies are shipped.
No Electron/Chromium, npm, tests, personal exports or development dependencies.
"""
import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from netease_music_insight import __version__


def copy_api(source, destination):
    def ignored(_directory, names):
        return [name for name in names if name in {'.git', '.github', '.bin', '__pycache__'}
                or name.lower().startswith(('readme', 'changelog', 'contributing'))
                or name.endswith(('.map', '.ts'))]
    destination.mkdir(parents=True)
    # Keep all runtime modules/data, not just the API endpoints currently used.
    # The helper's public folder is its own demo website/screenshots; our UI
    # and QR endpoints do not use it. Do not distribute that unrelated website.
    for name in ('node_modules', 'module', 'util', 'plugins', 'data'):
        if (source / name).exists():
            shutil.copytree(source / name, destination / name, ignore=ignored)
    for name in ('app.js', 'server.js', 'main.js', 'generateConfig.js', 'package.json', 'LICENSE'):
        shutil.copyfile(source / name, destination / name)


def run_checked(command, timeout=120):
    print('Check:', command[-1], flush=True)
    subprocess.run([str(item) for item in command], check=True, timeout=timeout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-dir', type=Path, required=True)
    parser.add_argument('--node', type=Path, default=shutil.which('node'))
    parser.add_argument('--gui-check', action='store_true')
    args = parser.parse_args()
    if sys.platform not in {'win32', 'darwin'}:
        raise SystemExit('Build on Windows or macOS using the matching native Python/Node')
    if not args.node or not args.node.is_file():
        raise SystemExit('Build requires a Node executable')
    node = args.node.resolve()
    node_arch = subprocess.check_output([str(node), '-p', 'process.arch'], text=True).strip()
    expected_arch = 'arm64' if platform.machine().lower() in {'arm64', 'aarch64'} else 'x64'
    if node_arch != expected_arch:
        raise SystemExit('Node and Python architectures must match')
    # A new build directory avoids deleting an existing package or user data.
    work = ROOT / 'build' / ('portable-' + sys.platform + '-' + expected_arch)
    work.mkdir(parents=True, exist_ok=False)
    api = work / 'netease-api'
    copy_api(args.api_dir.resolve(), api)
    node_license = work / 'NODE-LICENSE.txt'
    local_license = next((p for p in (node.parent / 'LICENSE', node.parent.parent / 'LICENSE')
                          if p.is_file()), None)
    if local_license:
        shutil.copyfile(local_license, node_license)
    else:
        version = subprocess.check_output([str(node), '--version'], text=True).strip()
        url = f'https://raw.githubusercontent.com/nodejs/node/{version}/LICENSE'
        with urllib.request.urlopen(url, timeout=60) as response:
            node_license.write_bytes(response.read())
    sep = os.pathsep
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir', '--windowed',
               '--clean', '--noupx', '--name', 'MusicInsight',
               '--distpath', str(work / 'dist'), '--workpath', str(work / 'pyinstaller'),
               '--specpath', str(work), '--collect-all', 'webview', '--collect-all', 'qqmusic_api',
               '--add-data', f'{ROOT / "netease_music_insight/frontend"}{sep}netease_music_insight/frontend',
               '--add-data', f'{api}{sep}runtime/netease-api',
               '--add-data', f'{node_license}{sep}runtime',
               '--add-binary', f'{node}{sep}runtime']
    for module in ('PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'tkinter', 'matplotlib',
                   'numpy', 'scipy', 'pytest', 'fastapi', 'uvicorn', 'httpx',
                   'PIL.AvifImagePlugin', 'PIL._avif'):
        command += ['--exclude-module', module]
    for package in ('requests', 'qrcode', 'pillow', 'qqmusic-api-python', 'pywebview'):
        command += ['--copy-metadata', package]
    if sys.platform == 'darwin':
        command += ['--osx-bundle-identifier', 'io.github.rhr-jz.musicinsight',
                    '--hidden-import', 'webview.platforms.cocoa']
    command.append(str(ROOT / 'run_desktop.py'))
    subprocess.run(command, check=True, cwd=ROOT)
    dist = work / 'dist'
    exe = (dist / 'MusicInsight.app/Contents/MacOS/MusicInsight' if sys.platform == 'darwin'
           else dist / 'MusicInsight/MusicInsight.exe')
    # Empty PATH proves shipped Node/API are used; never installed on first launch.
    saved_path = os.environ.get('PATH', '')
    try:
        os.environ['PATH'] = ''
        for argument in ('--version', '--smoke', '--web-smoke', '--runtime-smoke'):
            run_checked([exe, argument])
        run_checked([exe, '--cli', '--version'])
        run_checked([exe, '--local-web', '--smoke'])
    finally:
        os.environ['PATH'] = saved_path
    if args.gui_check:
        run_checked([exe, '--gui-smoke'], timeout=60)
    release = ROOT / 'dist'
    release.mkdir(exist_ok=True)
    platform_name = 'Windows-x64' if sys.platform == 'win32' else ('macOS-AppleSilicon' if expected_arch == 'arm64' else 'macOS-Intel')
    asset = release / f'MusicInsight-{platform_name}-{__version__}.zip'
    readme = ROOT / 'docs' / 'PORTABLE_START.txt'
    notices = ['LICENSE', 'LICENSE_MIT_ORIGINAL', 'THIRD_PARTY_LICENSES.md']
    if sys.platform == 'darwin':
        # ditto preserves the symlinks and executable bits of the signed app bundle.
        stage = work / 'share' / 'MusicInsight'
        stage.mkdir(parents=True)
        subprocess.run(['/usr/bin/ditto', str(dist / 'MusicInsight.app'), str(stage / 'MusicInsight.app')], check=True)
        for name in notices:
            shutil.copyfile(ROOT / name, stage / name)
        shutil.copyfile(readme, stage / 'START_HERE.txt')
        shutil.copyfile(node_license, stage / 'NODE-LICENSE.txt')
        launcher = stage / 'Open Local Web.command'
        launcher.write_text('#!/bin/bash\ncd "$(dirname "$0")"\nexec ./MusicInsight.app/Contents/MacOS/MusicInsight --local-web\n')
        launcher.chmod(0o755)
        subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(stage / 'MusicInsight.app')], check=True)
        subprocess.run(['/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(stage), str(asset)], check=True)
    else:
        stage = dist / 'MusicInsight'
        for name in notices:
            shutil.copyfile(ROOT / name, stage / name)
        shutil.copyfile(readme, stage / 'START_HERE.txt')
        shutil.copyfile(node_license, stage / 'NODE-LICENSE.txt')
        (stage / 'Open Local Web.cmd').write_text('@echo off\r\nstart "" "%~dp0MusicInsight.exe" --local-web\r\n', encoding='ascii')
        with zipfile.ZipFile(asset, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for file in sorted(stage.rglob('*')):
                if file.is_file():
                    archive.write(file, 'MusicInsight/' + file.relative_to(stage).as_posix())
    with asset.open('rb') as package:
        digest = hashlib.file_digest(package, 'sha256').hexdigest()
    asset.with_suffix('.zip.sha256').write_text(f'{digest}  {asset.name}\n', encoding='ascii')
    print(f'PACKAGE {asset.name}: {asset.stat().st_size / 1048576:.1f} MiB', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
