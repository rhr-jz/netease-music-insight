import subprocess
import unittest
from pathlib import Path
from unittest import mock

from netease_music_insight import platform_utils
from netease_music_insight.platform_utils import open_path


class PlatformUtilsTests(unittest.TestCase):
    @mock.patch("netease_music_insight.platform_utils.subprocess.run")
    def test_open_path_uses_macos_open(self, run):
        run.return_value.returncode = 0
        with mock.patch("netease_music_insight.platform_utils.sys.platform", "darwin"):
            self.assertTrue(open_path(Path("/tmp/二维码.png")))
        run.assert_called_once_with(
            ["open", "/tmp/二维码.png"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    @mock.patch("netease_music_insight.platform_utils.subprocess.run", side_effect=OSError)
    def test_open_path_failure_does_not_stop_export(self, _run):
        with mock.patch("netease_music_insight.platform_utils.sys.platform", "darwin"):
            self.assertFalse(open_path(Path("/missing")))

    def test_open_path_keeps_windows_behavior(self):
        with mock.patch("netease_music_insight.platform_utils.sys.platform", "win32"), \
             mock.patch.object(platform_utils.os, "startfile", create=True) as startfile:
            self.assertTrue(open_path(Path("C:/result")))
        startfile.assert_called_once_with(Path("C:/result"))

    def test_open_path_ignores_unsupported_platforms(self):
        with mock.patch("netease_music_insight.platform_utils.sys.platform", "linux"):
            self.assertFalse(open_path(Path("/tmp/result")))
