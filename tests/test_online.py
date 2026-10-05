"""Online security and lifecycle tests using the real Core and mocked providers."""
import contextlib
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import qrcode
from fastapi.testclient import TestClient

from netease_music_insight.errors import ExportCancelled
from netease_music_insight.report import build_data, write_reports
from netease_music_insight.service import MusicInsightService
from netease_music_insight.online.server import create_app
from netease_music_insight.online.settings import Settings
from netease_music_insight.online.security import RateLimiter
from netease_music_insight.online.storage import LocalTemporaryStorage


def until(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('Online job did not reach expected state')


class MockNetEase:
    expiry = False
    fail = False
    def __init__(self, _base, root, *, notify, present_qr, on_qr_expired,
                 check_cancel, output_dir, **kw):
        self.root, self.notify, self.present = root, notify, present_qr
        self.check, self.expired, self.output = check_cancel, on_qr_expired, output_dir
        self.private = 'MUSIC_U=private-fixture; qm_keyst=private-fixture'
    def login(self):
        qr = self.root / 'qr.png'
        qrcode.make('https://example.invalid/' + self.root.name).save(qr)
        self.present(qr, 'https://example.invalid/qr')
        self.notify('等待扫码……')
        if self.expiry:
            self.expired()
            self.present(qr, 'https://example.invalid/new')
        self.notify('已扫码，等待手机确认……')
        self.check()
        if self.fail:
            raise RuntimeError(self.private)
        return {'userId': self.root.name, 'nickname': '测试-' + self.root.name[-5:]}
    def export(self, profile):
        songs = [{'id': n, 'name': '歌-' + str(n), 'artists': '测试歌手',
                  'album': '测试专辑', 'duration_ms': 180000,
                  'liked_at': '2024-01-01T00:00:00+08:00'} for n in range(85)]
        playlists = [{'id': 'demo', 'name': '演示歌单', 'created_by_user': True,
                      'track_count': 85, 'tracks': songs,
                      'created_at': '2024-01-01T00:00:00+08:00'}]
        self.notify('✓ 喜欢音乐：85 首')
        self.notify('自建歌单：1 个 / 收藏歌单：0 个')
        self.notify('歌单歌曲分页：40/85')
        self.check()
        provider = 'qq_music' if isinstance(self, MockQQ) else 'netease'
        data = build_data(profile, songs, playlists, [], expected_liked=85,
                          expected_playlists=1, provider=provider)
        folder = self.output / provider
        write_reports(folder, data)
        return folder, data
    def drop_credentials(self):
        self.private = ''
    def logout(self):
        self.drop_credentials()


class MockQQ(MockNetEase):
    def __init__(self, root, **kw):
        present = kw.pop('present_qr')
        super().__init__('', root, present_qr=lambda p,u: present(p), **kw)
    async def login(self):
        return super().login()
    async def export(self, profile):
        return super().export(profile)
    async def logout(self):
        super().logout()


class OnlineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = 100.
        self.settings = Settings(environment='test', public_url='http://testserver',
                                 temporary_root=Path(self.temp.name), session_ttl=3600)
        factory = lambda *a, **kw: MusicInsightService(*a, api_context=lambda *_a, **_kw: contextlib.nullcontext('mock'), **kw)
        self.app = create_app(self.settings, service_factory=factory, clock=lambda: self.now)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.stack = contextlib.ExitStack()
        self.stack.enter_context(patch('netease_music_insight.service.NetEaseProvider', MockNetEase))
        self.stack.enter_context(patch('netease_music_insight.providers.qqmusic.QQMusicProvider', MockQQ))
        MockNetEase.expiry = MockNetEase.fail = False
        self.headers = {'Origin': 'http://testserver', 'X-Music-Insight-Request': '1'}
        self.create(self.client)
    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.stack.close()
        self.temp.cleanup()
    def create(self, client):
        r = client.post('/api/session', headers=self.headers)
        self.assertEqual(r.status_code,200)
        return r
    def post(self, path, data=None, client=None):
        return (client or self.client).post(path, headers=self.headers, json=data or {})
    def session(self, client=None):
        return self.app.state.sessions.get((client or self.client).cookies.get(self.settings.cookie_name))
    def run_job(self, provider='netease', client=None):
        client = client or self.client
        response = self.post('/api/jobs', {'provider':provider,'consent':True},client)
        self.assertEqual(response.status_code,202,response.text)
        sid = self.session(client)
        until(lambda: sid.bridge.snapshot()['state']['view']=='connected')
        self.assertEqual(self.post('/api/actions', {'method':'begin_export'},client).status_code,200)
        until(lambda: not sid.bridge.snapshot()['state']['busy'])
        sid.bridge._thread.join(2)
        self.assertIn(sid.bridge.get_job(response.json()['job_id'])['status'],('completed','partial'))
        return response.json()['job_id'],client.get('/api/snapshot').json()['state']
    def test_cookie_and_no_credentials_in_browser(self):
        r = self.create(self.client)
        cookie = r.headers['set-cookie']
        self.assertIn('HttpOnly',cookie)
        self.assertIn('SameSite=strict',cookie)
        self.assertNotIn(self.session().id,r.text)
        self.run_job()
        self.assertNotIn('private-fixture',self.client.get('/api/snapshot').text)
    def test_production_cookie_https_and_headers(self):
        with self.assertRaises(ValueError):
            Settings(environment='production')
        settings = Settings(environment='production',public_url='https://music.example',secret='x'*32)
        with TestClient(create_app(settings),base_url=settings.public_url) as client:
            r = client.post('/api/session',headers={'Origin':settings.public_url,'X-Music-Insight-Request':'1'})
            self.assertIn('__Host-music_insight=',r.headers['set-cookie'])
            self.assertIn('Secure',r.headers['set-cookie'])
            home = client.get('/')
            self.assertIn('style-nonce',home.text)
            self.assertNotIn('unsafe-inline',home.headers['content-security-policy'])
            self.assertIn('strict-transport-security',home.headers)
    def test_csrf_host_origin_and_input_limits(self):
        self.assertEqual(self.client.post('/api/jobs',json={'provider':'qq','consent':True}).status_code,403)
        self.assertEqual(self.client.get('/health',headers={'Host':'attacker.invalid'}).status_code,403)
        self.assertEqual(self.client.get('/api/snapshot',headers={'Origin':'https://attacker.invalid'}).status_code,403)
        self.assertEqual(self.post('/api/jobs',{'provider':'bad','consent':True,'secret':'private-fixture'}).status_code,400)
        self.assertEqual(self.client.post('/api/session',headers=self.headers,content='x'*17000).status_code,413)
        self.assertEqual(self.post('/api/actions',{'method':'open_logs'}).status_code,400)
        self.assertEqual(self.post('/api/library',{'page':0}).status_code,400)
        self.assertEqual(self.post('/api/jobs',{'provider':'qq','consent':False}).status_code,400)
    def test_two_users_job_qr_and_download_isolation(self):
        with contextlib.nullcontext(TestClient(self.app)) as second:
            self.create(second)
            a,sa = self.run_job(client=self.client)
            b,sb = self.run_job('qq',second)
            self.assertNotEqual(sa['result_folder'],sb['result_folder'])
            self.assertNotEqual(sa['nickname'],sb['nickname'])
            self.assertEqual(second.get('/api/jobs/'+a).status_code,404)
            self.assertEqual(self.client.get('/api/jobs/'+b).status_code,404)
            self.assertEqual(second.get('/api/download/'+sa['files'][0]['id']).status_code,404)
            self.assertNotEqual(self.session().bridge._storage.root,self.session(second).bridge._storage.root)
    def test_exports_zip_library_and_prompt_single_platform(self):
        _,state = self.run_job('qq')
        ids = {f['name']:f['id'] for f in state['files']}
        payload = self.client.get('/api/download/'+ids['music_for_ai.json']).json()
        self.assertEqual(payload['export_meta']['provider'],'qq_music')
        for page,count in [(1,40),(2,40),(3,5)]:
            r = self.post('/api/library',{'kind':'liked','page':page}).json()
            self.assertEqual((len(r['results']),r['total']),(count,85))
        playlists=self.post('/api/library',{'kind':'playlists'}).json()['results']
        r=self.post('/api/library',{'kind':'playlist','playlist_id':playlists[0]['id']}).json()
        self.assertEqual(r['total'],85)
        self.assertIn('没有可靠',self.post('/api/library',{'kind':'history'}).json()['reason'])
        self.assertNotIn(13,[t['number'] for t in state['topics']])
        for t in state['topics']:
            prompt=self.client.get('/api/topics/'+str(t['number'])).json()['topic']['prompt']
            self.assertIn('music_for_ai.json',prompt)
            self.assertIn('播放历史',prompt)
        blob=self.client.get('/api/download/'+ids['music-insight-export.zip']).content
        with ZipFile(io.BytesIO(blob)) as archive:
            self.assertIn('AI_ANALYSIS_GUIDE.md',archive.namelist())
            self.assertEqual(len([n for n in archive.namelist() if n.startswith('prompts/')]),len(state['topics']))
    def test_combined_13_topics_and_stale_result_revocation(self):
        _,state=self.run_job('all')
        self.assertEqual(state['data_filename'],'music_for_ai_combined.json')
        self.assertEqual(len(state['topics']),13)
        c=self.client.get('/api/comparison').json()['comparison']
        self.assertEqual(c['common_tracks'],85)
        ids=[f['id'] for f in state['files']]
        self.run_job('qq')
        self.assertNotIn('combined',self.session().bridge._datasets)
        for fid in ids:
            self.assertEqual(self.client.get('/api/download/'+fid).status_code,404)
    def test_partial_both_continues_other_provider(self):
        MockNetEase.fail=True
        # QQ overrides fail on its class to allow the second provider to work.
        with patch.object(MockQQ,'fail',False):
            job,state=self.run_job('all')
        self.assertEqual(self.session().bridge.get_job(job)['status'],'partial')
        self.assertEqual(state['data_filename'],'music_for_ai.json')
        self.assertNotIn('combined',self.session().bridge._datasets)
    def test_logout_revokes_files_and_deletes_directory(self):
        _,state=self.run_job()
        root=self.session().bridge._storage.root
        self.assertEqual(self.post('/api/logout').status_code,200)
        self.assertFalse(root.exists())
        self.assertEqual(self.client.get('/api/snapshot').status_code,401)
        self.assertEqual(self.client.get('/api/download/'+state['files'][0]['id']).status_code,401)
    def test_session_ttl_and_result_ttl_clean_up(self):
        root=self.session().bridge._storage.root
        self.now+=3601
        self.assertEqual(self.client.get('/api/snapshot').status_code,401)
        self.assertFalse(root.exists())
        self.create(self.client)
        self.run_job()
        root=self.session().bridge._storage.root
        self.settings.result_ttl=10
        self.now+=11
        self.assertEqual(self.client.get('/api/snapshot').status_code,401)
        self.assertFalse(root.exists())
    def test_cancel_refresh_and_logout_during_wait(self):
        MockNetEase.expiry=True
        r=self.post('/api/jobs',{'provider':'netease','consent':True})
        session=self.session()
        until(lambda: session.bridge.snapshot()['state']['login_status']=='二维码已过期')
        self.assertIsNone(session.bridge.snapshot()['state']['qr'])
        self.assertEqual(self.post('/api/actions',{'method':'refresh_qr'}).status_code,200)
        until(lambda: session.bridge.snapshot()['state']['view']=='connected')
        self.assertEqual(self.post('/api/actions',{'method':'cancel'}).status_code,200)
        session.bridge._thread.join(2)
        self.assertEqual(session.bridge.get_job(r.json()['job_id'])['status'],'cancelled')
        MockNetEase.expiry=False
        self.post('/api/jobs',{'provider':'qq','consent':True})
        until(lambda: session.bridge.snapshot()['state']['view']=='connected')
        root=session.bridge._storage.root
        self.post('/api/logout')
        session.bridge._thread.join(2)
        self.assertFalse(root.exists())
    def test_concurrency_and_rate_limit(self):
        self.app.state.jobs._slots = __import__('threading').BoundedSemaphore(1)
        self.assertEqual(self.post('/api/jobs',{'provider':'qq','consent':True}).status_code,202)
        with contextlib.nullcontext(TestClient(self.app)) as second:
            self.create(second)
            self.assertEqual(self.post('/api/jobs',{'provider':'qq','consent':True},second).status_code,409)
        self.post('/api/actions',{'method':'cancel'})
        for _ in range(21):
            r=self.client.post('/api/session',headers=self.headers)
        self.assertEqual(r.status_code,429)
    def test_failure_response_and_logs_do_not_include_credentials(self):
        MockNetEase.fail=True
        with self.assertLogs('music_insight.online',level='WARNING') as captured:
            r=self.post('/api/jobs',{'provider':'netease','consent':True})
            until(lambda: not self.session().bridge.snapshot()['state']['busy'])
        self.assertNotIn('private-fixture','\n'.join(captured.output))
        self.assertNotIn('private-fixture',self.client.get('/api/snapshot').text)
        self.assertEqual(self.session().bridge.get_job(r.json()['job_id'])['status'],'failed')
    def test_download_traversal_unpublished_files_and_invalid_actions(self):
        self.run_job()
        for path in ('/api/download/not-a-file','/api/download/%2e%2e%2fsecret','/assets/secrets.txt'):
            self.assertEqual(self.client.get(path).status_code,404)
        self.assertEqual(self.post('/api/actions',{'method':'select_source','args':[123]}).status_code,400)
        self.assertFalse(self.post('/api/actions',{'method':'select_source','args':['other-session']}).json()['ok'])
    def test_limiter_bounded_and_recovers(self):
        limiter=RateLimiter('x'*32,clock=lambda:self.now,max_keys=2)
        self.assertTrue(limiter.allow('a',1))
        self.assertFalse(limiter.allow('a',1))
        self.now+=61
        self.assertTrue(limiter.allow('a',1))
        limiter.allow('b',1);limiter.allow('c',1)
        self.assertEqual(len(limiter._buckets),2)

    def test_cleanup_retries_and_does_not_break_expiry(self):
        self.run_job()
        root=self.session().bridge._storage.root
        import shutil
        with patch('netease_music_insight.online.storage.shutil.rmtree',side_effect=PermissionError('synthetic file lease')):
            with self.assertLogs('music_insight.online',level='WARNING'):
                self.assertEqual(self.post('/api/logout').status_code,200)
            self.assertTrue(root.exists())
            self.assertEqual(self.client.get('/api/snapshot').status_code,401)
        self.app.state.sessions.reap()
        self.assertFalse(root.exists())
        self.assertEqual(self.app.state.sessions._retired,[])


if __name__=='__main__':
    unittest.main()
