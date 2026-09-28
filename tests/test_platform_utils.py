import subprocess
import unittest
from pathlib import Path
from unittest import mock

from netease_music_insight import platform_utils
from netease_music_insight.platform_utils import open_path
from netease_music_insight import bootstrap


class PlatformUtilsTests(unittest.TestCase):
    @mock.patch("netease_music_insight.platform_utils.subprocess.run")
    def test_open_path_uses_macos_open(self, run):
        run.return_value.returncode = 0
        path = Path("/tmp/二维码.png")
        with mock.patch("netease_music_insight.platform_utils.sys.platform", "darwin"):
            self.assertTrue(open_path(path))
        run.assert_called_once_with(
            ["open", str(path)],
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
        with mock.patch("netease_music_insight.platform_utils.sys.platform", "freebsd"):
            self.assertFalse(open_path(Path("/tmp/result")))

    @mock.patch("netease_music_insight.platform_utils.subprocess.run")
    def test_open_path_uses_linux_default_application(self, run):
        run.return_value.returncode = 0
        path = Path("/tmp/result")
        with mock.patch("netease_music_insight.platform_utils.sys.platform", "linux"):
            self.assertTrue(open_path(path))
        self.assertEqual(run.call_args.args[0], ["xdg-open", str(path)])

    def test_netease_requires_supported_node_on_macos(self):
        with mock.patch.object(bootstrap.sys, "platform", "darwin"), \
             mock.patch.object(bootstrap.shutil, "which", return_value="/usr/local/bin/node"), \
             mock.patch.object(bootstrap.subprocess, "run", return_value=mock.Mock(returncode=1)):
            with self.assertRaisesRegex(bootstrap.SetupError, "Node.js 18"):
                bootstrap._node(Path("/unused"), lambda _message: None)
