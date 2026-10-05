"""Prepared Node startup smoke, without contacting music account endpoints."""
import tempfile
from pathlib import Path
from .provider_runtime import prepared_context
from .settings import Settings

settings=Settings.from_env()
with tempfile.TemporaryDirectory(prefix='music-insight-runtime-check-') as folder:
    with prepared_context(settings.netease_api_dir)(Path(folder)) as base:
        assert base.startswith('http://127.0.0.1:')
print('Prepared NetEase runtime startup OK')
