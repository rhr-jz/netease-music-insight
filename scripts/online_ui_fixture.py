"""Browser test server: synthetic QR and real Core, never real account login."""
import contextlib
import sys
import tempfile
import time
from pathlib import Path

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
sys.path.insert(0,str(root/'tests'))
from test_online import MockNetEase, MockQQ
from netease_music_insight import service
from netease_music_insight.providers import qqmusic
from netease_music_insight.online.server import create_app
from netease_music_insight.online.settings import Settings
from netease_music_insight.service import MusicInsightService
import uvicorn

class SlowNetEase(MockNetEase):
    def login(self):
        original=self.present
        def present(*args):
            result=original(*args)
            time.sleep(1)
            return result
        self.present=present
        return super().login()
class SlowQQ(MockQQ):
    async def login(self):
        original=self.present
        def present(*args):
            result=original(*args)
            time.sleep(1)
            return result
        self.present=present
        return await super().login()

service.NetEaseProvider=SlowNetEase
qqmusic.QQMusicProvider=SlowQQ
factory=lambda *a,**kw: MusicInsightService(*a,api_context=lambda *_a,**_kw:contextlib.nullcontext('mock'),**kw)
port=int(sys.argv[1]) if len(sys.argv)>1 else 58003
with tempfile.TemporaryDirectory(prefix='music-insight-ui-fixture-') as temp:
    settings=Settings(environment='test',public_url=f'http://127.0.0.1:{port}',temporary_root=Path(temp))
    uvicorn.run(create_app(settings,service_factory=factory),host='127.0.0.1',port=port,access_log=False)
