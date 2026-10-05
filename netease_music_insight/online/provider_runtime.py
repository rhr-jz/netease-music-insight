"""Run a prebuilt NetEase helper per job; no runtime downloads or npm install."""
import contextlib
import os
import shutil
import socket
import subprocess
import time
import json
from pathlib import Path

import requests

from ..bootstrap import SetupError


def ready(api_dir, node=None):
    return bool(api_dir and (node or shutil.which("node")) and
                (Path(api_dir) / "app.js").is_file() and
                (Path(api_dir) / "node_modules/express").is_dir())


def prepared_context(api_dir, cancellation=None, node=None):
    @contextlib.contextmanager
    def run(root, notify=None):
        if not ready(api_dir, node):
            raise SetupError("服务器的网易云组件未准备好。")
        scratch = Path(root) / ".node"
        scratch.mkdir(parents=True, exist_ok=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {k: v for k, v in os.environ.items() if k.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "LANG"}}
        env.update(HOST="127.0.0.1", PORT=str(port), NODE_ENV="production",
                   TMPDIR=str(scratch), TEMP=str(scratch), TMP=str(scratch))
        # Skip the helper's npm version check and boot-time anonymous login.
        # Its API/cache and Node tmpdir are isolated for every job.
        entry = scratch / "server.cjs"
        entry.write_text("const fs=require('fs'),path=require('path');" +
            "fs.writeFileSync(path.join(require('os').tmpdir(),'anonymous_token'),'');" +
            "require(" + json.dumps(str(Path(api_dir).resolve() / "server.js")) +
            ").serveNcmApi({checkVersion:false}).catch(()=>process.exit(1));", encoding="utf-8")
        process = subprocess.Popen([str(node or shutil.which("node")), str(entry)],
                                   cwd=scratch, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        def stop_process():
            if process.poll() is None:
                try:
                    process.terminate()
                except OSError:
                    pass
        if cancellation:
            cancellation.register_cleanup(stop_process)
        try:
            base = f"http://127.0.0.1:{port}"
            probe = requests.Session()
            probe.trust_env = False
            for _ in range(40):
                if cancellation:
                    cancellation.check()
                if process.poll() is not None:
                    raise SetupError("服务器网易云组件启动失败。")
                try:
                    if probe.get(base, timeout=0.5).status_code < 500:
                        break
                except requests.RequestException:
                    pass
                time.sleep(0.2)
            else:
                raise SetupError("服务器网易云组件启动超时。")
            yield base
        finally:
            probe.close()
            if cancellation:
                cancellation.unregister_cleanup(stop_process)
            stop_process()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    return run
