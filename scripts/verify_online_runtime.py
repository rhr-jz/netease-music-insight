"""Check prepared runtime and real QR generation without an account login."""
import asyncio
import sys
import tempfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from netease_music_insight.online.provider_runtime import prepared_context
from netease_music_insight.online.app import configure_logging
from netease_music_insight.api import MusicApi

def main():
    configure_logging()
    results=[]
    with tempfile.TemporaryDirectory(prefix='music-insight-runtime-smoke-') as temp:
        folder=Path(temp)
        try:
            with prepared_context(root/'build/online-api')(folder) as base:
                api=MusicApi(base)
                key=api.get('/login/qr/key')['data']['unikey']
                qr=api.get('/login/qr/create',{'key':key})['data']['qrurl']
                assert isinstance(qr,str) and qr.startswith('https://')
                api.session.close()
            results.append('NetEase prepared runtime + real QR: OK')
        except Exception as exc:
            from netease_music_insight.bootstrap import SetupError
            results.append('NetEase prepared runtime + real QR: FAILED ('+type(exc).__name__+')'+(' '+str(exc) if isinstance(exc,SetupError) else ''))
        async def qq():
            from qqmusic_api import Client,Platform
            from qqmusic_api.models.login import QRLoginType
            from qqmusic_api.modules.login_utils import QRCodeLoginSession
            client=Client(platform=Platform.ANDROID,device_path=str(folder/'qq-device.json'))
            session=QRCodeLoginSession(client.login,QRLoginType.MOBILE,timeout_seconds=30)
            try:
                qr=await asyncio.wait_for(session.get_qrcode(),timeout=35)
                assert qr.save(folder)
            finally:
                await client.close()
        try:
            asyncio.run(qq())
            results.append('QQ Music real QR: OK')
        except Exception as exc:
            results.append('QQ Music real QR: FAILED ('+type(exc).__name__+')')
    print('\n'.join(results))
    return 1 if any('FAILED' in value for value in results) else 0

if __name__=='__main__':
    raise SystemExit(main())
