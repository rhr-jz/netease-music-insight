"""Portable apps must use their bundled runtime and writable user data paths."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from netease_music_insight import bootstrap
from netease_music_insight.desktop import app, clipboard


class PortableTests(unittest.TestCase):
    def test_bundle_components_do_not_depend_on_path_or_data_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / 'runtime'
            (runtime / 'netease-api/node_modules/express').mkdir(parents=True)
            (runtime / 'netease-api/server.js').touch()
            (runtime / 'node').touch()
            with patch.object(bootstrap.sys, 'frozen', True, create=True), \
                 patch.object(bootstrap.sys, '_MEIPASS', temp, create=True), \
                 patch.object(bootstrap.sys, 'platform', 'darwin'):
                self.assertEqual(bootstrap.bundled_runtime(), (runtime / 'node', runtime / 'netease-api'))
                (runtime / 'node').unlink()
                with self.assertRaises(bootstrap.SetupError):
                    bootstrap.bundled_runtime()

    def test_frozen_macos_never_writes_into_app_bundle(self):
        with patch.object(app.sys, 'frozen', True, create=True), \
             patch.object(app.sys, 'platform', 'darwin'), \
             patch.object(app.sys, 'executable', '/Applications/MusicInsight.app/Contents/MacOS/MusicInsight'):
            self.assertEqual(app.app_root(), Path.home() / 'Library/Application Support/MusicInsight')

    def test_frozen_windows_uses_local_appdata(self):
        with patch.object(app.sys, 'frozen', True, create=True), \
             patch.object(app.sys, 'platform', 'win32'), \
             patch.dict(app.os.environ, {'LOCALAPPDATA': '/user-data'}):
            self.assertEqual(app.app_root(), Path('/user-data/MusicInsight'))

    def test_macos_clipboard_passes_unicode_as_stdin(self):
        with patch.object(clipboard.sys, 'platform', 'darwin'), \
             patch.object(clipboard.subprocess, 'run') as run:
            clipboard.copy_text('中文 Prompt\n完整内容')
            self.assertEqual(run.call_args.args[0], ['/usr/bin/pbcopy'])
            self.assertEqual(run.call_args.kwargs['input'].decode('utf-8'), '中文 Prompt\n完整内容')
