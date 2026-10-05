// Exercise the actual browser/WASM Core using synthetic data only.
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import http from 'node:http';
import { readFile, mkdir, stat } from 'node:fs/promises';
import { resolve, dirname, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const site = resolve(root, '_site');
const basePath = '/netease-music-insight/';
const screenshots = resolve(root, 'build/browser/screenshots');
await mkdir(screenshots, { recursive: true });
const mime = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.wasm': 'application/wasm', '.svg': 'image/svg+xml' };
const served = [];
const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  served.push({ method: req.method, path: url.pathname, query: url.search });
  if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405); res.end(); return; }
  try {
    if (!url.pathname.startsWith(basePath)) throw new Error('Not found');
    const name = url.pathname.slice(basePath.length) || 'index.html';
    const path = resolve(site, decodeURIComponent(name));
    if (!path.startsWith(site + sep) || !(await stat(path)).isFile()) throw new Error('Not found');
    res.writeHead(200, { 'Content-Type': mime[extname(path)] || 'application/octet-stream', 'Cache-Control': 'no-cache' });
    res.end(req.method === 'HEAD' ? undefined : await readFile(path));
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ headless: true, ...(process.env.MUSIC_BROWSER_CHANNEL ? { channel: process.env.MUSIC_BROWSER_CHANNEL } : {}) });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, permissions: ['clipboard-read', 'clipboard-write'] });
const requests = [], errors = [];
context.on('request', request => requests.push({ url: request.url(), method: request.method() }));
const page = await context.newPage();
page.on('pageerror', error => errors.push(String(error)));
const clickNav = async text => page.getByRole('navigation').getByRole('button', { name: text, exact: false }).click();
const settle = async () => page.locator('#busy').waitFor({ state: 'hidden', timeout: 120000 });
const demo = JSON.parse(await readFile(resolve(site, 'demo.json'), 'utf8'));
const selectJSON = async (data, name = 'music_for_ai.json') => {
  await page.locator('#files').setInputFiles({ name, mimeType: 'application/json', buffer: Buffer.from(typeof data === 'string' ? data : JSON.stringify(data)) });
  await settle();
};
let checks = 0;
function pass(name) { checks++; console.log(`PASS ${name}`); }
try {
  await page.goto(origin + basePath);
  await page.getByRole('heading', { name: '听见自己。' }).waitFor();
  await page.screenshot({ path: resolve(screenshots, 'home.png') });
  pass('home renders without a backend');
  await clickNav('我的音乐');
  await page.getByRole('heading', { name: '先打开一份音乐数据' }).waitFor();
  pass('empty state guides file import');
  await page.getByRole('button', { name: '先看演示', exact: true }).click();
  await settle();
  await page.locator('.metrics').waitFor();
  assert.equal(await page.locator('.metric strong').first().textContent(), '60');
  assert.equal(await page.locator('#source-select').inputValue(), 'combined');
  await page.screenshot({ path: resolve(screenshots, 'dashboard.png') });
  pass('browser Python Core imports demo and builds Combined');
  await clickNav('AI 分析');
  assert.equal(await page.locator('.topic-card').count(), 13);
  await page.screenshot({ path: resolve(screenshots, 'ai.png') });
  for (let number = 1; number <= 13; number++) {
    await page.locator(`[data-topic="${number}"]`).click(); await settle();
    const prompt = await page.locator('#prompt-text').inputValue();
    assert.ok(prompt.startsWith('请完整读取我上传的 music_for_ai_combined.json。'));
    assert.ok(prompt.includes('不要把播放历史缺失解释为用户不重复听歌'));
    await page.getByRole('button', { name: '复制 Prompt', exact: true }).click();
    await page.locator('.copy-ok').getByText('✓ 已复制').waitFor();
    // Windows clipboard uses CRLF while textarea.value normalizes to LF.
    assert.equal((await page.evaluate(() => navigator.clipboard.readText())).replace(/\r\n/g, '\n'), prompt);
    await page.getByRole('button', { name: '返回分析方向', exact: false }).click();
  }
  pass('all 13 prompts open, remain complete, and copy via Clipboard API');
  await page.locator('#source-select').selectOption('qq_music'); await settle();
  assert.equal(await page.locator('.topic-card').count(), 12);
  await page.locator('[data-topic="4"]').click(); await settle();
  assert.ok((await page.locator('#prompt-text').inputValue()).includes('QQ 音乐播放历史不可用'));
  pass('single-platform topics and missing QQ history adapt');
  await clickNav('导出');
  for (const name of ['music_for_ai.json', 'music_summary.md', 'AI_ANALYSIS_GUIDE.md']) {
    const downloadEvent = page.waitForEvent('download');
    await page.locator(`[data-download="${name}"]`).click();
    const download = await downloadEvent; await settle();
    assert.equal(download.suggestedFilename(), name);
    const content = await readFile(await download.path(), 'utf8');
    assert.ok(content.length > 100);
    if (name.endsWith('.json')) assert.equal(JSON.parse(content).export_meta.provider, 'qq_music');
  }
  const zipEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: '下载完整导出包', exact: false }).click();
  const zip = await zipEvent; await settle();
  assert.equal((await readFile(await zip.path())).subarray(0, 2).toString(), 'PK');
  pass('JSON, summary, guide, and ZIP download from on-device Core');
  const attack = structuredClone(demo[1]);
  attack.liked_songs[0].name = '<img src="https://example.invalid/private" onerror="window.pwned=true">';
  await selectJSON(attack);
  assert.equal(await page.locator('#source-select').inputValue(), 'qq_music');
  assert.equal(await page.locator('.demo-tag').count(), 0);
  await page.locator('#song-list').getByText('<img src=', { exact: false }).waitFor();
  assert.equal(await page.locator('#song-list img').count(), 0);
  assert.equal(await page.evaluate(() => window.pwned), undefined);
  pass('untrusted imported names render as text and never fetch avatars/images');
  await selectJSON('{bad json');
  await page.locator('#notice').getByText('JSON 无法读取', { exact: false }).waitFor();
  assert.equal(await page.locator('.metric strong').first().textContent(), '24');
  pass('invalid import keeps the previous data');
  const net = structuredClone(demo[0]);
  net.liked_songs = Array.from({ length: 12000 }, (_, i) => ({ id: String(i), name: `歌曲${i}`, artists: '测试歌手', album: '测试专辑', duration_ms: 190000 }));
  net.song_catalog = net.liked_songs;
  net.playlists = [];
  await selectJSON(net);
  await page.locator('#source-select').selectOption('netease'); await settle();
  await page.locator('#search-count').getByText('12,000', { exact: false }).waitFor();
  assert.equal(await page.locator('.song-row:not(.heading)').count(), 40);
  await page.locator('#search').fill('歌曲11999');
  await page.locator('#search-count').getByText('共 1 首', { exact: true }).waitFor();
  pass('12,000 tracks stay in the worker; search and paging keep DOM bounded');
  await clickNav('设置 / 隐私');
  await page.getByRole('button', { name: '清空数据', exact: true }).click(); await settle();
  await clickNav('我的音乐');
  await page.getByRole('heading', { name: '先打开一份音乐数据' }).waitFor();
  assert.equal(await page.evaluate(() => localStorage.length), 0);
  assert.equal(await page.evaluate(async () => (await indexedDB.databases()).length), 0);
  pass('clear releases the session; no music in persistent browser storage');
  await page.locator('#offline-status').getByText('网页已可离线打开').waitFor({ timeout: 60000 });
  await context.setOffline(true);
  await page.reload();
  await selectJSON(demo[1]);
  await page.locator('.metrics').waitFor();
  await clickNav('AI 分析');
  await page.locator('[data-topic="2"]').click(); await settle();
  assert.ok((await page.locator('#prompt-text').inputValue()).includes('music_for_ai.json'));
  pass('offline reload, file import, statistics, and prompts work');
  await context.setOffline(false);
  for (const viewport of [{ width: 390, height: 844 }, { width: 768, height: 1024 }, { width: 1024, height: 700 }]) {
    await page.setViewportSize(viewport);
    for (const id of ['home', 'import', 'music', 'ai', 'export', 'privacy']) {
      await page.locator(`[data-view="${id}"]`).first().click();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `horizontal overflow: ${id} ${viewport.width}`);
    }
    await clickNav('我的音乐');
    await page.screenshot({ path: resolve(screenshots, `music-${viewport.width}.png`) });
  }
  pass('phone, tablet, and small desktop layouts have no horizontal overflow');
  // Edge's native download popup emits edge:// UI-resource requests in this
  // context. Those are browser internals, not outgoing website traffic.
  const networkRequests = requests.filter(r => !/^(edge|chrome):/.test(r.url));
  const external = networkRequests.filter(r => !r.url.startsWith(origin + '/'));
  assert.deepEqual(external, []);
  assert.ok(networkRequests.every(r => r.method === 'GET'));
  assert.ok(served.every(r => !r.query && ['GET', 'HEAD'].includes(r.method)));
  assert.deepEqual(errors, []);
  pass('no external requests, music uploads, tracking queries, or page errors');
  console.log(`Browser checks: ${checks} passed`);
} finally {
  await context.close(); await browser.close(); await new Promise(resolve => server.close(resolve));
}
