"""Prepare and run the existing API wrapper only on 127.0.0.1."""
import contextlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path


API_ARCHIVE = "https://github.com/TH911/NeteaseCloudMusicApi/archive/refs/heads/main.zip"
NODE_VERSION = "24.16.0"
NODE_ARCHIVE = f"https://nodejs.org/dist/v{NODE_VERSION}/node-v{NODE_VERSION}-win-x64.zip"


class SetupError(RuntimeError):
    pass


def _download(url, target):
    request = urllib.request.Request(url, headers={"User-Agent": "NetEaseMusicInsight/1.0"})
    with urllib.request.urlopen(request, timeout=90) as source, target.open("wb") as dest:
        shutil.copyfileobj(source, dest)


def _unzip_safe(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise SetupError("下载的压缩包包含非法路径。")
        zf.extractall(destination)


def _node(root, notify):
    installed = shutil.which("node")
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if installed and npm:
        try:
            version = subprocess.run(
                [installed, "-e", "process.exit(Number(process.versions.node.split('.')[0]) >= 18 ? 0 : 1)"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False,
            )
            if version.returncode == 0:
                return installed, npm
        except (OSError, subprocess.TimeoutExpired):
            pass
    if sys.platform != "win32":
        raise SetupError("网易云导出需要 Node.js 18 或更新版本，请安装或更新后重试。")
    node_dir = root / ".runtime" / f"node-v{NODE_VERSION}-win-x64"
    node = node_dir / "node.exe"
    npm = node_dir / "npm.cmd"
    if not node.exists() or not npm.exists():
        notify("首次运行：正在准备本地运行组件（需要联网，约几分钟）……")
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "node.zip"
            _download(NODE_ARCHIVE, archive)
            _unzip_safe(archive, root / ".runtime")
    if not node.exists() or not npm.exists():
        raise SetupError("Node.js 组件下载不完整，请检查网络后重试。")
    return str(node), str(npm)


def _api_source(root, notify):
    api_dir = root / "api"
    if (api_dir / "app.js").exists() and (api_dir / "package.json").exists():
        return api_dir
    notify("首次运行：正在下载本地网易云接口组件……")
    with tempfile.TemporaryDirectory() as temp:
        archive = Path(temp) / "api.zip"
        unpacked = Path(temp) / "unpacked"
        _download(API_ARCHIVE, archive)
        _unzip_safe(archive, unpacked)
        candidates = list(unpacked.glob("*/package.json"))
        if len(candidates) != 1:
            raise SetupError("接口组件压缩包结构异常。")
        if api_dir.exists():
            raise SetupError("本地 api 文件夹不完整，请先移走该文件夹再重试。")
        shutil.move(str(candidates[0].parent), api_dir)
    return api_dir


def _ensure_dependencies(api_dir, npm, notify):
    if (api_dir / "node_modules" / "express").exists():
        return
    notify("首次运行：正在安装本地接口依赖……")
    command = [npm, "ci" if (api_dir / "package-lock.json").exists() else "install",
               "--omit=dev", "--ignore-scripts", "--no-audit", "--no-fund"]
    result = subprocess.run(command, cwd=api_dir, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, text=True, timeout=600)
    if result.returncode:
        raise SetupError("本地接口依赖安装失败。请检查网络，稍后重试。")


@contextlib.contextmanager
def local_api(root: Path, notify=None):
    notify = notify or (lambda message: None)
    try:
        node, npm = _node(root, notify)
        api_dir = _api_source(root, notify)
        _ensure_dependencies(api_dir, npm, notify)
    except (OSError, urllib.error.URLError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        raise SetupError("运行组件准备失败。请检查网络和文件夹写入权限后重试。") from exc
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ.copy()
    env.update({"HOST": "127.0.0.1", "PORT": str(port), "NODE_ENV": "production"})
    process = subprocess.Popen([node, "app.js"], cwd=api_dir, env=env,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import requests
        base = f"http://127.0.0.1:{port}"
        for _ in range(40):
            if process.poll() is not None:
                raise SetupError("本地接口启动失败，请重新运行；如果重复失败，请提交 Issue。")
            try:
                response = requests.get(base, timeout=1)
                if response.status_code < 500:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.5)
        else:
            raise SetupError("本地接口启动超时，请重新运行。")
        yield base
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
