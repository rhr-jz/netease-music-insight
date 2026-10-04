"""Explicit Online Web launcher; production requires a configured HTTPS origin."""
import argparse
import logging
import logging.config
import os
import sys
from pathlib import Path

from .settings import Settings


def configure_logging():
    # Never format arbitrary third-party exceptions or requests in online logs.
    folder = Path(os.getenv("MUSIC_INSIGHT_LOG_DIR", "logs"))
    folder.mkdir(parents=True, exist_ok=True)
    logging.config.dictConfig({"version": 1, "disable_existing_loggers": True,
        "formatters": {"safe": {"format": "%(asctime)s %(levelname)s %(message)s"}},
        "handlers": {"safe": {"class": "logging.StreamHandler", "formatter": "safe"},
                     "file": {"class": "logging.handlers.RotatingFileHandler", "formatter": "safe",
                              "filename": str(folder / "online.log"), "maxBytes": 1048576,
                              "backupCount": 2, "encoding": "utf-8"}},
        "loggers": {"music_insight.online": {"handlers": ["safe", "file"], "level": "INFO", "propagate": False}},
        "root": {"handlers": [], "level": "CRITICAL"}})


def main(argv=None):
    parser = argparse.ArgumentParser(description="Music Insight Online Web")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)
    from .server import create_app
    if args.smoke:
        from fastapi.testclient import TestClient
        settings = Settings(environment="test", public_url="http://testserver")
        with TestClient(create_app(settings)) as client:
            assert client.get("/health").status_code == 200
            assert "Music Insight" in client.get("/").text
            assert client.post("/api/session", headers={"Origin": settings.public_url, "X-Music-Insight-Request": "1"}).status_code == 200
            assert client.get("/api/snapshot").json()["state"]["view"] == "home"
        print("Music Insight Online Web smoke OK")
        return 0
    configure_logging()
    settings = Settings.from_env()
    if os.getenv("WEB_CONCURRENCY", "1") != "1":
        raise ValueError("This version requires a single instance / worker")
    import uvicorn
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port,
                workers=1, access_log=False, proxy_headers=False, log_config=None,
                timeout_keep_alive=5, limit_concurrency=256)
    return 0


if __name__ == "__main__":
    sys.exit(main())
