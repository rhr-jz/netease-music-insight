const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const format = value => Number(value || 0).toLocaleString('zh-CN');
const date = value => { const d = new Date(value); return value && !Number.isNaN(d.getTime()) ? d.toLocaleString('zh-CN') : '未知'; };
const releaseURL = 'https://github.com/rhr-jz/netease-music-insight/releases/latest';
const navItems = [['home', '⌂', '首页'], ['import', '↥', '打开数据'], ['music', '◉', '我的音乐'], ['ai', '✦', 'AI 分析'], ['export', '↓', '导出'], ['privacy', '◇', '设置 / 隐私']];
const names = Object.fromEntries(navItems.map(([id, , label]) => [id, label]));
let view = Object.hasOwn(names, location.hash.slice(1)) ? location.hash.slice(1) : 'home';
let state = { dashboard: null, sources: [], topics: [], demo: false };
let activeTopic = null, copied = false, worker, serial = 0, busy = false, importTask = null;
let query = '', searchPage = 1, searchSerial = 0, searchTimer, noticeTimer;
const pending = new Map();

function notice(message, error = false) {
  clearTimeout(noticeTimer);
  $('#notice').textContent = message;
  $('#notice').classList.toggle('error', error);
  $('#notice').hidden = false;
  noticeTimer = setTimeout(() => { $('#notice').hidden = true; }, error ? 12000 : 5500);
}
function busyState(value, message = '正在本机处理音乐数据…') {
  busy = value;
  $('#busy').hidden = !value;
  $('#busy-text').textContent = message;
  $('#cancel-import').hidden = !importTask;
  document.querySelectorAll('[data-mutate]').forEach(button => { button.disabled = value; });
}
function api(method, args = [], buffers) {
  if (!worker) {
    worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' });
    worker.onmessage = ({ data }) => {
      if (data.status) { if (busy) $('#busy-text').textContent = data.status; return; }
      const job = pending.get(data.id);
      if (!job) return;
      pending.delete(data.id); clearTimeout(job.timer);
      data.ok ? job.resolve(data.result) : job.reject(new Error(data.message));
    };
    worker.onerror = event => {
      event.preventDefault();
      for (const job of pending.values()) { clearTimeout(job.timer); job.reject(new Error('浏览器运行环境中断，请刷新页面后重新打开数据。')); }
      pending.clear(); worker.terminate(); worker = null;
      state = { dashboard: null, sources: [], topics: [], demo: false }; activeTopic = null; render();
    };
  }
  return new Promise((resolve, reject) => {
    const id = ++serial;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error('准备时间较长，请检查网络后重试。已选择的文件不会上传。')); }, 180000);
    pending.set(id, { resolve, reject, timer });
    worker.postMessage({ id, method, args, buffers }, buffers || []);
  });
}
async function task(message, action) {
  if (busy) return;
  busyState(true, message);
  try { await action(); } catch (error) { notice(error.message || '操作未完成，请重试。', true); }
  finally { importTask = null; busyState(false); }
}
function navigate(next) {
  if (!Object.hasOwn(names, next)) return;
  view = next; activeTopic = null; copied = false;
  history.replaceState(null, '', `#${view}`);
  render(); window.scrollTo({ top: 0 });
}
function head(kicker, title, detail) { return `<div class="page-header"><div class="eyebrow">${kicker}</div><h2>${title}</h2><p>${detail}</p></div>`; }
function button(label, action, kind = '', extra = '') { return `<button class="btn ${kind}" data-action="${action}" ${extra}>${label}</button>`; }
function sourceSelector() { return `<select class="source-select" id="source-select" aria-label="选择音乐数据" ${busy ? 'disabled' : ''} data-mutate>${state.sources.map(item => `<option value="${esc(item.id)}" ${item.id === state.selected ? 'selected' : ''}>${esc(item.label)}</option>`).join('')}</select>`; }
function dataBadge() { return state.demo ? '<span class="demo-tag">合成演示数据</span>' : ''; }
function empty(title, description) { return `${head('YOUR MUSIC', title, description)}<section class="card empty"><h3>先打开一份音乐数据</h3><p>选择 Music Insight 导出的 JSON，即可在浏览器中查看。文件内容只在本机处理。</p>${button('打开音乐数据', 'choose', 'primary', 'data-mutate')} ${button('先看演示', 'demo', 'ghost', 'data-mutate')}</section>`; }

function home() {
  return `<section class="hero"><div><div class="eyebrow">A SPACE FOR YOUR MUSIC</div><h1>听见<em>自己。</em></h1><p class="lead">整理你的音乐数据，<br>看见属于自己的音乐世界。</p><div class="hero-actions">${button('打开音乐数据　↗', 'choose', 'primary', 'data-mutate')}${button(state.dashboard ? '回到我的音乐' : '先看演示', state.dashboard ? 'music' : 'demo', 'ghost', state.dashboard ? '' : 'data-mutate')}</div><p class="small-note">选择本地 JSON · 无需上传文件 · 无需 AI API Key</p></div><div class="vinyl-wrap" aria-hidden="true"><div class="vinyl"><div class="vinyl-label"></div></div><span class="vinyl-caption">YOUR OWN FREQUENCY</span></div></section>
    <section class="intro-grid"><div><div class="intro-num">01</div><h3>看见音乐的轮廓</h3><p>收藏、歌手、专辑与歌单。先从自己的音乐事实开始。</p></div><div><div class="intro-num">02</div><h3>找到想问的问题</h3><p>审美、成长与音乐地图。为每一个方向准备独立 Prompt。</p></div><div><div class="intro-num">03</div><h3>探索由你决定</h3><p>下载数据，选择你喜欢的 AI。什么时候分享，由你决定。</p></div></section>
    <div class="scope-banner">网页版目前读取已有导出数据。首次获取音乐数据，请用<a href="${releaseURL}" target="_blank" rel="noopener noreferrer">桌面版</a>扫码整理，再在这里打开 JSON。${button('了解使用方式', 'import', 'small ghost')}</div>`;
}
function importPage() {
  return `${head('OPEN YOUR MUSIC', '让音乐数据，留在你身边。', '网易云、QQ 音乐和联合数据都能读取。文件只进入当前标签页，不上传。')}
    <section class="import-zone" id="drop-zone"><div class="import-symbol" aria-hidden="true">↥</div><h3>把音乐数据拖到这里</h3><p>选择 <strong>music_for_ai.json</strong> 或 <strong>music_for_ai_combined.json</strong>。也可以同时选择两个平台各一份文件，自动生成联合数据。</p>${button('选择本地 JSON 文件', 'choose', 'primary', 'data-mutate')}<p class="small-note">每个文件最多 64 MB。请不要选择 Cookie、Token 或登录凭证文件。</p></section>
    <div class="grid-two mt"><section class="card"><h3>第一次使用，还没有数据？</h3><ol class="steps"><li>下载并打开 Music Insight 桌面版。</li><li>用音乐 App 扫码，点击“开始整理我的音乐”。</li><li>在“导出”页找到 JSON，在这里打开。</li></ol><a class="btn small" href="${releaseURL}" target="_blank" rel="noopener noreferrer">获取桌面版 ↗</a></section><section class="card"><h3>想先看看能做什么？</h3><p class="mt">使用合成示例，体验 Dashboard、跨平台视图和完整 AI Prompt。所有演示数据都明确标记，不包含真实账号。</p><div class="mt">${button('打开演示数据', 'demo', 'small', 'data-mutate')}</div></section></div>`;
}
function chart(rows) { const max = Math.max(1, ...rows.map(row => row.count)); return `<div class="chart">${rows.map(row => `<div class="chart-row"><span class="chart-name" title="${esc(row.name)}">${esc(row.name)}</span><progress class="bar" max="${max}" value="${row.count}" aria-label="${esc(row.name)} ${row.count} 首"></progress><span class="count">${format(row.count)}</span></div>`).join('') || '<p>当前没有可统计的数据。</p>'}</div>`; }
function music() {
  if (!state.dashboard) return empty('我的音乐', '从你实际拥有的数据，认识自己的音乐收藏。');
  const d = state.dashboard, t = state.time_coverage;
  return `${head('YOUR MUSIC', `我的音乐${dataBadge()}`, '这里只呈现音乐事实；关于偏好的解释，留给你选择的 AI。')}
    <div class="data-toolbar"><div class="meta">${esc(d.source)} · 数据时间 ${esc(date(d.updated_at))}${d.status === 'partial' ? '<br>部分数据未能获取，分析时请留意导出文件中的缺口。' : ''}</div>${sourceSelector()}</div>
    <section class="metrics" aria-label="音乐统计">${[['liked', '喜欢歌曲'], ['unique', '不同歌曲'], ['artists', '歌手'], ['playlists', '歌单']].map(([key, label]) => `<div class="metric"><strong>${format(d[key])}</strong><span>${label}</span></div>`).join('')}</section>
    <div class="grid-two"><section class="card chart-card"><div class="eyebrow">TOP ARTISTS</div><h3>喜欢歌曲中常出现的歌手</h3><p>按喜欢歌曲中的出现次数统计${state.selected === 'combined' ? '，两个平台分别计数' : ''}。</p>${chart(d.top_artists)}</section><section class="card chart-card"><div class="eyebrow">TOP ALBUMS</div><h3>反复遇见的专辑</h3><p>按喜欢歌曲中的出现次数统计。</p><div class="mt">${d.top_albums.map((row, i) => `<div class="rank-row"><span>${String(i + 1).padStart(2, '0')} · ${esc(row.name)}</span><span>${format(row.count)} 首</span></div>`).join('') || '<p>暂无专辑数据。</p>'}</div></section></div>
    <div class="grid-two mt"><section class="card"><h3>歌单的规模</h3><div class="facts"><span><strong>${format(d.created_playlists)}</strong>自建歌单</span><span><strong>${format(d.subscribed_playlists)}</strong>收藏歌单</span><span><strong>${format(d.largest_playlist)}</strong>最大歌单歌曲数</span></div></section><section class="card"><h3>时间数据覆盖</h3><div class="facts"><span><strong>${format(t.liked_songs_with_time)}</strong>歌曲收藏时间</span><span><strong>${format(t.playlists_with_creation_time)}</strong>歌单创建时间</span><span><strong>${format(t.playlists_with_subscription_time)}</strong>歌单收藏时间</span></div><p class="small-note mt">只使用接口实际返回的时间，缺失值不会按列表顺序推算。</p></section></div>
    ${d.platforms.length > 1 ? `<section class="card mt"><h3>两个平台，各自的音乐</h3>${d.platforms.map(p => `<div class="platform-row"><strong>${esc(p.name)}</strong><span>喜欢 ${format(p.liked)} · 歌单 ${format(p.playlists)} · 不同歌曲 ${format(p.unique)}</span></div>`).join('')}<p class="small-note">联合去重沿用桌面版的保守匹配规则，不确定的版本保持分开。</p></section>` : ''}
    <div class="section-head"><h3>浏览你的音乐</h3><p>搜索歌曲、歌手或专辑，每页最多显示 40 首。</p></div><section class="card"><div class="search-wrap"><input class="search" id="search" type="search" maxlength="200" placeholder="搜索歌曲 / 歌手 / 专辑" aria-label="搜索本地音乐" value="${esc(query)}"><span class="small-note" id="search-count">正在读取…</span></div><div id="song-list" class="song-list" aria-live="polite"></div><div id="pagination" class="pagination"></div></section>
    <div class="scope-banner">接下来，选择一个你真正想了解的问题。${button('探索 AI 分析　→', 'ai', 'small')}</div>`;
}
function ai() {
  if (!state.dashboard) return empty('探索你的音乐世界', '打开数据后，分析方向会根据可用字段自动调整。');
  if (activeTopic) {
    const t = activeTopic;
    return `<div class="topic-detail"><button class="text-button back" data-action="ai-back">← 返回分析方向</button>${head(`ANALYSIS ${String(t.number).padStart(2, '0')}`, esc(t.title), esc(t.question))}${t.reason ? `<div class="scope-banner">${esc(t.reason)}</div>` : ''}<div class="section-head"><h3>AI 会分析</h3></div><div class="scope-chips">${t.scope.split(/[、；]/).filter(Boolean).map(s => `<span>${esc(s)}</span>`).join('')}</div><h3>完整 Prompt</h3><p class="small-note mt">可以独立使用，已包含文件名、数据范围与缺失说明。</p><textarea id="prompt-text" class="prompt-box mt" readonly aria-label="完整 AI Prompt">${esc(t.prompt)}</textarea><div class="copy-row">${button('复制 Prompt', 'copy', 'primary')}${button('下载对应数据', 'download-data', '', 'data-mutate')}<span class="copy-ok" role="status">${copied ? '✓ 已复制' : ''}</span></div><section class="card"><h3>怎么使用？</h3><ol class="steps"><li>打开你喜欢、且支持文件上传的 AI。</li><li>上传 <strong>${esc(t.filename)}</strong>。</li><li>点击“复制 Prompt”，粘贴给 AI。</li><li>开始分析，并让 AI 指出具体歌曲或歌单证据。</li></ol><p>你可以自行选择 ChatGPT、Claude、Gemini、DeepSeek、通义千问或其他支持文件的 AI。上传前，请确认你愿意把音乐数据交给所选服务。</p></section></div>`;
  }
  return `${head('AI ANALYSIS', `探索你的音乐世界${dataBadge()}`, '请选择你感兴趣的方向。每个 Prompt 都可以独立复制使用。')}<div class="data-toolbar"><span class="small-note">当前数据：${esc(state.dashboard.source)}</span>${sourceSelector()}</div>
    <div class="routes"><section class="route"><h3>第一次使用</h3><p>全景画像 → 真实音乐审美 → 核心歌手 → 音乐地图 → 系统听歌计划</p></section><section class="route"><h3>只想轻松看看</h3><p>全景画像 → 年度总结 → 同龄人音乐谈资</p></section><section class="route"><h3>认真培养音乐品味</h3><p>真实音乐审美 → 核心歌手 → 音乐地图 → 审美盲区 → 系统听歌计划</p></section></div>
    <div class="section-head"><h3>从一个问题开始</h3><p>无需 API Key。Music Insight 准备数据和 Prompt，分析由你选择的 AI 完成。</p></div><section class="topic-grid">${state.topics.map(t => `<button class="topic-card" data-topic="${t.number}" data-mutate><span class="number">${String(t.number).padStart(2, '0')} / EXPLORE</span><strong>${esc(t.title)}</strong><small>${esc(t.question)}</small>${t.reason ? '<small class="limited">数据有限 · 点击查看说明</small>' : ''}</button>`).join('')}</section>`;
}
function exportPage() {
  if (!state.dashboard) return empty('导出 AI 数据', '数据文件、音乐摘要和 AI 指南，都在本机生成。');
  const files = [[state.filename, '适合 AI 阅读的音乐数据'], [state.selected === 'combined' ? 'music_summary_combined.md' : 'music_summary.md', '音乐统计、收藏时间与数据缺口'], ['AI_ANALYSIS_GUIDE.md', '所有可用分析方向与完整 Prompt']];
  return `${head('YOUR FILES', `带上你的音乐世界${dataBadge()}`, '选择需要的文件，直接保存到设备。下载内容由当前浏览器生成。')}<div class="data-toolbar"><span class="small-note">当前数据：${esc(state.dashboard.source)}</span>${sourceSelector()}</div><section class="card">${files.map(([name, desc], i) => `<div class="file-row"><div class="file-glyph">${i ? 'MD' : 'JSON'}</div><div class="file-info"><strong>${esc(name)}</strong><p>${esc(desc)}</p></div><button class="btn small" data-download="${esc(name)}" data-mutate>下载</button></div>`).join('')}</section><div class="hero-actions">${button('下载完整导出包　↓', 'download-all', 'primary', 'data-mutate')}<span class="small-note">ZIP 同时包含独立 prompts/ 文件。</span></div><section class="card"><h3>把数据交给 AI，需要哪些文件？</h3><p class="mt">上传 <strong>${esc(state.filename)}</strong>，再从“AI 分析”复制你感兴趣的 Prompt。网页不会自动连接 AI 或上传你的数据。</p><div class="mt">${button('选择分析方向', 'ai', 'small')}</div></section>`;
}
function privacy() {
  return `${head('YOUR DATA, YOUR CHOICE', '让数据留在你的设备。', '音乐文件在浏览器内处理。每一次主动分享，都由你决定。')}<div class="privacy-grid"><section class="card"><h3>文件不会上传</h3><p>读取、统计、联合匹配、搜索、Prompt 和导出均在当前标签页运行。网页不读取账号密码，不接收 Cookie 或 Token。</p></section><section class="card"><h3>没有使用统计或追踪</h3><p>没有广告、埋点、追踪 Cookie、远程字体或外部 CDN。不会加载数据文件里的头像或其他远程图片。</p></section><section class="card"><h3>关闭后需要重新打开数据</h3><p>音乐数据只保存在标签页内存中，不写入 LocalStorage、IndexedDB 或网页离线缓存。清空数据或关闭页面后，重新选择 JSON 即可恢复。</p></section><section class="card"><h3>托管平台仍有访问记录</h3><p>若部署到 GitHub Pages，GitHub 会为安全目的记录访客 IP。我们无法控制托管平台的基础访问日志；音乐文件内容不会传给它。<a href="https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages#data-collection" target="_blank" rel="noopener noreferrer">查看 GitHub 官方说明</a>。</p></section></div>
    <section class="card mt"><div class="setting-row"><div><h3>外观</h3><p>选择适合当前环境的主题。</p></div>${button(document.documentElement.dataset.theme === 'light' ? '切换深色' : '切换浅色', 'theme', 'small')}</div><div class="setting-row"><div><h3>当前音乐数据</h3><p>${state.dashboard ? `已打开 ${esc(state.dashboard.source)}${state.demo ? '（合成演示）' : ''}。清空只影响此标签页。` : '尚未打开任何音乐数据。'}</p></div>${button('清空数据', 'clear', 'small', 'data-mutate')}</div><div class="setting-row"><div><h3>离线浏览</h3><p>网页资源缓存完成后，可断网重新打开页面和本地 JSON。缓存只包含程序和演示文件。</p></div><span class="small-note" id="offline-detail">正在检查…</span></div></section>
    <div class="scope-banner">此预览支持已有音乐数据的浏览与导出。公网扫码抓取、GitHub Pages 部署和国内稳定访问方案尚待确认。GitHub 域名不能保证在所有国内网络下稳定访问。</div><div class="link-row"><a href="https://github.com/rhr-jz/netease-music-insight" target="_blank" rel="noopener noreferrer">项目源代码 ↗</a><a href="./LICENSE.txt" target="_blank" rel="noopener noreferrer">项目许可</a><a href="./THIRD_PARTY.txt" target="_blank" rel="noopener noreferrer">第三方许可</a></div>`;
}
const pages = { home, import: importPage, music, ai, export: exportPage, privacy };
function render() {
  $('#navigation').innerHTML = navItems.map(([id, icon, label]) => `<button class="nav-button ${id === view ? 'active' : ''}" data-view="${id}" ${id === view ? 'aria-current="page"' : ''}><span class="nav-icon" aria-hidden="true">${icon}</span>${label}</button>`).join('');
  $('#breadcrumb').textContent = `MUSIC INSIGHT / ${names[view]}`;
  $('#page').innerHTML = pages[view]();
  document.title = `${names[view]} · Music Insight`;
  document.querySelectorAll('[data-mutate]').forEach(b => { b.disabled = busy; });
  if (view === 'music' && state.dashboard) updateSearch();
  if (view === 'privacy') offlineDetail();
}
async function importFiles(files) {
  if (busy || !files.length) return;
  if (files.length > 2 || files.some(file => !file.name.toLowerCase().endsWith('.json') || file.size > 64 * 1024 * 1024)) {
    notice('请选择最多两份 JSON 音乐数据文件，每个文件不超过 64 MB。', true); return;
  }
  await task('正在读取本地文件，内容不会上传…', async () => {
    importTask = { cancelled: false }; $('#cancel-import').hidden = false;
    const buffers = await Promise.all(files.map(file => file.arrayBuffer()));
    if (importTask.cancelled) { notice('已取消导入，原来的数据仍然保留。'); return; }
    await api('prepare', [], buffers);
    if (importTask.cancelled) { await api('discard'); notice('已取消导入，原来的数据仍然保留。'); return; }
    state = await api('commit'); query = ''; searchPage = 1; navigate('music');
    notice(state.selected === 'combined' ? '已在浏览器内整理两个平台，并生成联合数据。' : '音乐数据已打开，文件没有上传。');
  });
}
async function updateSearch() {
  const sequence = ++searchSerial, source = state.selected;
  try {
    const result = await api('search', [query, searchPage]);
    if (sequence !== searchSerial || view !== 'music' || source !== state.selected) return;
    searchPage = result.page;
    $('#search-count').textContent = `共 ${format(result.total)} 首`;
    $('#song-list').innerHTML = '<div class="song-row heading"><span>歌曲</span><span>歌手</span><span>专辑</span></div>' + (result.results.map(song => `<div class="song-row"><span>${esc(song.name || '未命名歌曲')}</span><span>${esc(song.artists || '未知')}</span><span>${esc(song.album || '未知')}</span></div>`).join('') || '<p class="small-note mt">没有找到匹配的歌曲。</p>');
    $('#pagination').innerHTML = `<span>第 ${result.page} / ${result.pages} 页</span><div class="pagination-buttons">${button('上一页', 'previous', 'small', result.page <= 1 ? 'disabled' : '')}${button('下一页', 'next', 'small', result.page >= result.pages ? 'disabled' : '')}</div>`;
  } catch (error) { if (view === 'music') notice(error.message, true); }
}
async function download(name) {
  await task('正在本机生成导出文件…', async () => {
    const file = await api('download', [name]);
    const content = file.binary ? Uint8Array.from(atob(file.content), c => c.charCodeAt(0)) : file.content;
    const url = URL.createObjectURL(new Blob([content], { type: file.mime }));
    const a = document.createElement('a'); a.href = url; a.download = file.name; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000); notice('文件已生成，请在浏览器下载列表中查看。');
  });
}
document.addEventListener('click', async event => {
  const node = event.target.closest('[data-view],[data-action],[data-topic],[data-download]');
  if (!node || node.disabled) return;
  if (node.dataset.view) return navigate(node.dataset.view);
  if (node.dataset.topic) return task('正在准备完整 Prompt…', async () => { activeTopic = await api('topic', [Number(node.dataset.topic)]); copied = false; render(); window.scrollTo({ top: 0 }); });
  if (node.dataset.download) return download(node.dataset.download);
  const action = node.dataset.action;
  if (Object.hasOwn(names, action)) return navigate(action);
  if (action === 'choose') { if (!busy) $('#files').click(); }
  else if (action === 'demo') await task('正在打开合成演示…', async () => { state = await api('demo'); query = ''; searchPage = 1; navigate('music'); notice('这是合成演示数据，不代表你的音乐账号。'); });
  else if (action === 'ai-back') { activeTopic = null; copied = false; render(); }
  else if (action === 'copy' && activeTopic) {
    try { await navigator.clipboard.writeText(activeTopic.prompt); copied = true; $('.copy-ok').textContent = '✓ 已复制'; }
    catch { $('#prompt-text').focus(); $('#prompt-text').select(); notice('浏览器暂不允许自动复制，已选中全文，请手动复制。', true); }
  } else if (action === 'download-data') await download(state.filename);
  else if (action === 'download-all') await download('MusicInsight-export.zip');
  else if (action === 'theme') { document.documentElement.dataset.theme = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light'; render(); }
  else if (action === 'clear') await task('正在清空当前数据…', async () => { if (worker) state = await api('clear'); activeTopic = null; query = ''; searchPage = 1; render(); notice('当前标签页的数据已清空，原始文件没有改变。'); });
  else if (action === 'previous' || action === 'next') { searchPage += action === 'next' ? 1 : -1; updateSearch(); }
});
$('#files').addEventListener('change', event => { const files = [...event.target.files]; event.target.value = ''; importFiles(files); });
document.addEventListener('change', event => {
  if (event.target.id === 'source-select') task('正在切换数据…', async () => { state = await api('select', [event.target.value]); activeTopic = null; copied = false; query = ''; searchPage = 1; render(); });
});
document.addEventListener('input', event => {
  if (event.target.id !== 'search') return;
  query = event.target.value; searchPage = 1; clearTimeout(searchTimer);
  searchTimer = setTimeout(updateSearch, 180);
});
document.addEventListener('dragover', event => { if (event.target.closest('#drop-zone')) { event.preventDefault(); $('#drop-zone').classList.add('dragover'); } });
document.addEventListener('dragleave', event => { if (event.target.closest('#drop-zone')) $('#drop-zone').classList.remove('dragover'); });
document.addEventListener('drop', event => { if (event.target.closest('#drop-zone')) { event.preventDefault(); $('#drop-zone').classList.remove('dragover'); importFiles([...event.dataTransfer.files]); } });
$('#cancel-import').addEventListener('click', () => { if (importTask) { importTask.cancelled = true; $('#cancel-import').hidden = true; $('#busy-text').textContent = '已取消，等待当前读取结束…'; } });
window.addEventListener('hashchange', () => { const next = location.hash.slice(1); if (Object.hasOwn(names, next)) navigate(next); });

let offlineReady = false;
function offlineDetail() { if ($('#offline-detail')) $('#offline-detail').textContent = offlineReady ? '网页资源已缓存' : '网页资源准备中'; }
if ('serviceWorker' in navigator && window.isSecureContext) {
  navigator.serviceWorker.addEventListener('message', event => {
    if (event.data === 'offline-ready') { offlineReady = true; $('#offline-status').textContent = '网页已可离线打开'; offlineDetail(); }
  });
  navigator.serviceWorker.register('./sw.js').then(async () => {
    const registration = await navigator.serviceWorker.ready;
    registration.active?.postMessage('offline-status');
  }).catch(() => { $('#offline-status').textContent = '当前浏览器未启用离线缓存'; });
}
render();
