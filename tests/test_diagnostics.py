"""Credential redaction for errors raised by music API clients."""
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from netease_music_insight.diagnostics import RedactingFormatter, redact_text
from netease_music_insight.utils import atomic_json


class DiagnosticsTests(unittest.TestCase):
    def test_exception_chain_and_qr_are_redacted(self):
        secret = "example-secret-credential-123456"
        try:
            raise RuntimeError(
                "GET /login?cookie=MUSIC_U%3D" + secret +
                "&qm_keyst=" + secret + " Authorization: Bearer " + secret +
                " data:image/png;base64,QUJDREVGRw=="
            )
        except RuntimeError:
            record = logging.LogRecord("music-insight", logging.ERROR, __file__, 1,
                                       "request failed", (), sys.exc_info())
        formatted = RedactingFormatter("%(message)s").format(record)
        self.assertNotIn(secret, formatted)
        self.assertNotIn("QUJDREVGRw==", formatted)
        self.assertIn("[redacted]", formatted)
        self.assertEqual(redact_text("qqmusic_key=" + secret), "qqmusic_key=[redacted]")
        self.assertNotIn(secret, redact_text('{"cookie": "' + secret + '"}'))
        self.assertNotIn("123456789", redact_text("musicid=123456789"))

    @unittest.skipUnless(os.name == "nt", "Windows file replacement behavior")
    def test_atomic_write_retries_transient_windows_file_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "含 空格" / "settings.json"
            target.parent.mkdir()
            target.write_text('{"old":true}', encoding="utf-8")
            original = Path.replace
            calls = 0

            def transient(source, destination):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise PermissionError("file temporarily held by scanner")
                return original(source, destination)

            with patch.object(Path, "replace", transient), patch(
                    "netease_music_insight.utils.time.sleep"):
                atomic_json(target, {"value": "中文"})
            self.assertEqual(calls, 2)
            self.assertIn("中文", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
