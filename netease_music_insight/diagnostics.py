"""Redact credentials before any technical exception reaches local log files."""
import logging
import re
from pathlib import Path


_PAIR = re.compile(
    r"(?i)\b(cookie|token|access_token|refresh_token|qm_keyst|qqmusic_key|"
    r"MUSIC_U|MUSIC_A|MUSIC_R_T|csrf|unikey|qrurl|key|password|passwd|"
    r"credential|musicid|encrypt_uin|uid)\b"
    r"([\"']?\s*(?:=|:|%3D)\s*[\"']?)([^\s&;\"'<>)\]}]+)"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+")
_QR_IMAGE = re.compile(r"(?i)data:image/[^;\s]+;base64,[A-Za-z0-9+/=]+")


def redact_text(value):
    text = str(value)
    text = _QR_IMAGE.sub("[redacted QR image]", text)
    text = _BEARER.sub("Bearer [redacted]", text)
    return _PAIR.sub(lambda match: match.group(1) + match.group(2) + "[redacted]", text)


class RedactingFormatter(logging.Formatter):
    def format(self, record):
        return redact_text(super().format(record))


def configure_error_logging(root):
    folder = Path(root) / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "error.log"
    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)
    formatter = RedactingFormatter("%(asctime)s %(levelname)s %(message)s")
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == target.resolve():
            handler.setFormatter(formatter)
            return handler
    handler = logging.FileHandler(target, encoding="utf-8")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return handler
