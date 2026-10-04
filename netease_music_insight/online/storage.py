"""Session-owned temporary storage with opaque download manifests."""
import mimetypes
import secrets
import shutil
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from threading import RLock
from zipfile import ZIP_DEFLATED, ZipFile


class StorageBackend(ABC):
    @abstractmethod
    def publish(self, source, folder): ...

    @abstractmethod
    def read(self, file_id): ...

    @abstractmethod
    def close(self): ...


class LocalTemporaryStorage(StorageBackend):
    def __init__(self, parent=None):
        if parent:
            Path(parent).mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="music-insight-session-", dir=parent)).resolve()
        self._lock = RLock()
        self._manifest = {}
        self._sources = {}
        self.revoked = False

    def publish(self, source, folder):
        with self._lock:
            if self.revoked:
                raise FileNotFoundError("Session closed")
            folder = Path(folder).resolve(strict=True)
            if not folder.is_relative_to(self.root) or folder.is_symlink():
                raise ValueError("Result must belong to this session")
            names = {"music_for_ai.json", "music_for_ai_combined.json", "music_summary.md",
                     "music_summary_combined.md", "AI_ANALYSIS_GUIDE.md", "AI_ANALYSIS_PROMPT.md",
                     "AI_ANALYSIS_PROMPT_COMBINED.md"}
            paths = [p for p in folder.iterdir() if p.name in names and p.is_file() and not p.is_symlink()]
            prompt_dir = folder / "prompts"
            if prompt_dir.is_dir() and not prompt_dir.is_symlink():
                paths += [p for p in prompt_dir.glob("*.md") if p.is_file() and not p.is_symlink()]
            if not paths:
                raise ValueError("No export files")
            archive_path = folder / "music-insight-export.zip"
            if archive_path.is_symlink():
                raise ValueError("Invalid archive")
            with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
                for path in paths:
                    resolved = path.resolve(strict=True)
                    if not resolved.is_relative_to(folder):
                        raise ValueError("Invalid result path")
                    archive.write(path, path.relative_to(folder).as_posix())
            paths.append(archive_path)
            for file_id in self._sources.pop(source, []):
                self._manifest.pop(file_id, None)
            entries = []
            for path in paths:
                file_id = secrets.token_urlsafe(18)
                name = path.relative_to(folder).as_posix()
                self._manifest[file_id] = (path, name)
                entries.append({"id": file_id, "name": name, "description": "独立 Prompt" if name.startswith("prompts/") else "音乐数据与分析文件"})
            self._sources[source] = [item["id"] for item in entries]
            return entries

    def read(self, file_id):
        # Copy to memory while holding the lease: TTL/logout cannot delete a
        # file between validation and reading. Already sent bytes are irrevocable.
        with self._lock:
            if self.revoked or file_id not in self._manifest:
                raise FileNotFoundError("Result unavailable")
            path, name = self._manifest[file_id]
            resolved = path.resolve(strict=True)
            if path.is_symlink() or not resolved.is_relative_to(self.root) or not resolved.is_file():
                raise FileNotFoundError("Result unavailable")
            return resolved.read_bytes(), name, mimetypes.guess_type(name)[0] or "application/octet-stream"

    def unpublish(self, source):
        with self._lock:
            for file_id in self._sources.pop(source, []):
                self._manifest.pop(file_id, None)

    def revoke(self):
        with self._lock:
            self.revoked = True
            self._manifest.clear()
            self._sources.clear()

    def close(self):
        self.revoke()
        # The root is created here, never derived from a cookie or request path.
        if self.root.exists() and not self.root.is_symlink():
            shutil.rmtree(self.root)
