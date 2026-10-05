"""Single-instance deployment configuration. Never accept provider URLs from users."""
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass
class Settings:
    environment: str = "development"
    public_url: str = "http://127.0.0.1:8000"
    host: str = "127.0.0.1"
    port: int = 8000
    session_ttl: int = 3600
    result_ttl: int = 3600
    max_active_jobs: int = 5
    max_sessions: int = 100
    secret: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    netease_api_dir: Path | None = None
    temporary_root: Path | None = None

    def __post_init__(self):
        self.public_url = self.public_url.rstrip("/")
        url = urlsplit(self.public_url)
        if url.scheme not in {"http", "https"} or not url.netloc or url.path or url.query or url.fragment or url.username:
            raise ValueError("MUSIC_INSIGHT_PUBLIC_URL must be an origin without a path")
        if self.environment not in {"development", "production", "test"}:
            raise ValueError("Invalid environment")
        if self.environment == "production" and url.scheme != "https":
            raise ValueError("Production requires an HTTPS public URL")
        if self.environment == "development" and (url.hostname not in {"127.0.0.1", "localhost"} or self.host not in {"127.0.0.1", "localhost"}):
            raise ValueError("Development mode must stay on loopback")
        if not all(1 <= n <= 86400 for n in (self.session_ttl, self.result_ttl)):
            raise ValueError("TTL must be between 1 and 86400 seconds")
        if not 1 <= self.max_active_jobs <= 50 or not 1 <= self.max_sessions <= 1000:
            raise ValueError("Invalid concurrency/session limits")
        if len(self.secret) < 32 or not 1 <= self.port <= 65535:
            raise ValueError("Secret must be at least 32 characters; port must be valid")

    @property
    def secure(self):
        return self.environment == "production"

    @property
    def cookie_name(self):
        return "__Host-music_insight" if self.secure else "music_insight_online"

    @classmethod
    def from_env(cls):
        return cls(environment=os.getenv("MUSIC_INSIGHT_ENV", "development"),
                   public_url=os.getenv("MUSIC_INSIGHT_PUBLIC_URL", "http://127.0.0.1:8000"),
                   host=os.getenv("MUSIC_INSIGHT_HOST", "127.0.0.1"),
                   port=int(os.getenv("MUSIC_INSIGHT_PORT", "8000")),
                   session_ttl=int(os.getenv("MUSIC_INSIGHT_SESSION_TTL", "3600")),
                   result_ttl=int(os.getenv("MUSIC_INSIGHT_RESULT_TTL", "3600")),
                   max_active_jobs=int(os.getenv("MUSIC_INSIGHT_MAX_ACTIVE_JOBS", "5")),
                   max_sessions=int(os.getenv("MUSIC_INSIGHT_MAX_SESSIONS", "100")),
                   secret=os.getenv("MUSIC_INSIGHT_SECRET") or secrets.token_urlsafe(32),
                   netease_api_dir=Path(os.environ["MUSIC_INSIGHT_NETEASE_API_DIR"]) if os.getenv("MUSIC_INSIGHT_NETEASE_API_DIR") else None,
                   temporary_root=Path(os.environ["MUSIC_INSIGHT_TEMP_ROOT"]) if os.getenv("MUSIC_INSIGHT_TEMP_ROOT") else None)
