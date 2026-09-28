"""UI-neutral progress events for CLI, desktop, and local web adapters."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MusicEvent:
    kind: str
    provider: str
    message: str = ""
    current: int | None = None
    total: int | None = None
    path: Path | None = None
    details: dict = field(default_factory=dict)

    def as_dict(self):
        """Return a transport-friendly copy; never add credentials here."""
        return {"kind": self.kind, "provider": self.provider, "message": self.message,
                "current": self.current, "total": self.total,
                "path": str(self.path) if self.path is not None else None,
                "details": self.details.copy()}
