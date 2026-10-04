    'use strict';
    let state = null, revision = -1, bridgeReady = false, polling = false;
    let activeTopic = null, copied = false, lastFolder = null, searchTimer = null;
    const API=window.MusicInsightAPI, isOnline=API.mode==='online', isWeb=API.mode!=='desktop';
    let expired=false, consent=false, libraryKind='catalog',libraryQuery='',libraryPage=1,playlistId=null,librarySerial=0;
    if(isWeb)document.documentElement.classList.add('web-mode');
    async function callCore(name,...args){return API.call(name,...args);}
    const content = document.getElementById('content');
    const nav = document.getElementById('nav');
    const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const labels = {home:'首页', platforms:'选择平台', login:'连接账号', connected:'已连接', progress:'整理中', music:'我的音乐',library:'音乐档案',cross:'跨平台',privacy:'隐私', ai:'AI 分析', export:'导出', settings:'设置', error:'遇到问题'};
    const navItems = [['home','⌂','首页'],['music','◉','我的音乐'],['library','♫','音乐档案'],['cross','⇄','跨平台'],['ai','✦','AI 分析'],['export','⇩','导出'],['settings','⚙','设置'],['privacy','◇','隐私']];
    function button(text, action, cls='') { return `<button class="btn ${cls}" data-action="${action}">${text}</button>`; }
    function header(kicker, title, detail='') { return `<div class="page-header"><div class="eyebrow">${kicker}</div><h2>${title}</h2>${detail ? `<p>${detail}</p>` : ''}</div>`; }
    function toast() { return state.toast ? `<div class="toast">${esc(state.toast)}</div>` : ''; }
    function home() { return `${toast()}${expired?'<div class="toast">会话已结束，临时数据已清理。点击开始探索创建新会话。</div>':''}<div class="hero"><div><div class="eyebrow">A SPACE FOR YOUR MUSIC</div><h1>听见<span>自己。</span></h1><p class="lead">连接网易云音乐和 QQ 音乐，<br>整理属于你的音乐记忆，<br>通过数据与 AI 重新认识自己的音乐审美。</p><div class="hero-actions">${button('开始探索我的音乐','explore','primary')}${button('了解它能做什么','go-privacy','ghost')}</div><p class="small-note">收藏只是音乐留下的痕迹。下一步探索，由你决定。</p></div><div class="vinyl-wrap"><div class="vinyl-halo"><div class="vinyl"><div class="vinyl-center"></div></div></div></div></div><div class="feature-grid"><section class="card"><h3>Online Web · 无需安装</h3><p>扫码、整理、Dashboard、AI Prompt 和导出。数据临时经过部署服务器，会话结束后删除。</p>${isOnline?button('了解在线隐私','go-privacy','small'):'<p class="small-note">需要部署者提供在线网址，当前使用本地版本。</p>'}</section><section class="card"><h3>Desktop / Local Web · 本地私人空间</h3><p>音乐数据留在自己的电脑，适合长期使用。</p><a class="btn small" href="https://github.com/rhr-jz/netease-music-insight/releases/latest" target="_blank" rel="noopener noreferrer">获取桌面版 ↗</a></section></div><div class="hero-foot">网易云音乐 · QQ 音乐 · 跨平台整理 · Dashboard · AI · 导出</div>`; }
    function platforms() { return `${toast()}${header('CONNECT YOUR MUSIC','选择你的音乐平台',isOnline?'无需输入密码或复制 Cookie。开始前请了解数据会临时经过部署服务器。':'每一步都有引导，数据保存在这台电脑上。')}${isOnline?`<section class="card consent-box"><label><input id="online-consent" type="checkbox" ${consent?'checked':''}> 我已阅读隐私说明，同意服务器为本次整理临时处理平台凭据和音乐数据。</label><p class="small-note">默认最多 1 小时，退出可提前清除；不建立云端账号，不自动发送给 AI。${button('隐私说明','go-privacy','small')}</p></section>`:''}<div class="cards">${[['netease','net','♪','网易云音乐','喜欢歌曲<br>自建与收藏歌单<br>平台可获取的播放记录','连接网易云'],['qq','qq','♫','QQ 音乐','我喜欢<br>自建与收藏歌单<br>可访问的音乐元数据','连接 QQ 音乐'],['all','all','⇄','两个平台','依次连接两个平台<br>保守匹配相同录音<br>形成联合音乐档案','联合整理']].map(([id,c,icon,name,detail,label])=>`<section class="card platform-card"><div class="platform-icon ${c}">${icon}</div><h3>${name}</h3><p>${detail}</p>${button(label,'start-'+id,'primary')}</section>`).join('')}</div>`; }
    function login() { const expired = state.login_status === '二维码已过期'; return `${toast()}<div class="flow-panel">${header('CONNECT ACCOUNT',`连接${esc(state.provider_name || '音乐平台')}`,'请用对应 App 扫描并确认。手机浏览器请使用另一设备扫码，或保存图片后尝试 App 识别。')}<div class="qr-frame">${state.qr ? '<img id="qr-image" alt="登录二维码">' : '<div class="qr-placeholder">正在准备<br>登录二维码</div>'}</div><div class="status-pill">${esc(state.login_status)}</div><p style="margin:17px 0 0">${esc(state.message || `请使用${state.provider_name || '对应音乐'} App 扫描`)}</p><div class="flow-actions">${expired ? button('重新生成二维码','refresh','primary') : ''}${state.qr?button('保存二维码','save-qr','small'):''}${button('取消连接','cancel','ghost')}</div></div>`; }
    function connected() { const first = Array.from(state.nickname || '音').slice(0,1).join(''); return `${toast()}<div class="flow-panel">${header('CONNECTED','已经连接好了','现在可以开始整理你的音乐世界。')}<div class="mono-avatar">${esc(first)}</div><div class="connected-check">✓ 已连接</div><h2 style="font-size:29px">${esc(state.nickname)}</h2><p>${esc(state.provider_name)}</p><div class="flow-actions">${button('开始整理我的音乐　→','begin','primary')}${button('取消','cancel','ghost')}</div></div>`; }
    function progress() { const p=state.progress, ratio=p.tracks_total ? Math.max(0,Math.min(100,Math.round(p.tracks_current/p.tracks_total*100))) : 0; const value=(v,suffix='')=>v===null||v===undefined?'等待中':`✓ ${v}${suffix}`; return `${toast()}${header('ORGANIZING','正在整理你的音乐世界…',esc(state.message || p.phase || '你可以继续使用电脑，窗口会保持响应。'))}<section class="card progress-card"><div class="progress-row"><span>用户资料</span><span class="progress-value done">✓ 已读取</span></div><div class="progress-row"><span>喜欢歌曲</span><span class="progress-value ${p.liked!==null?'done':''}">${value(p.liked,' 首')}</span></div><div class="progress-row"><span>歌单</span><span class="progress-value ${p.playlists!==null?'done':''}">${value(p.playlists,' 个')}</span></div><div class="progress-row"><span>歌单歌曲</span><span class="progress-value">${p.tracks_total?`${p.tracks_current} / ${p.tracks_total} · ${ratio}%`:'等待中'}</span><div class="bar-track" role="progressbar" aria-valuenow="${ratio}" aria-valuemin="0" aria-valuemax="100"><div class="bar-fill" style="width:${ratio}%"></div></div></div><div class="progress-row"><span>当前歌曲分页</span><span class="progress-value">${p.page_total?`${p.page_current} / ${p.page_total}`:"等待中"}</span></div><div class="progress-row"><span>播放记录</span><span class="progress-value ${p.history!==null?'done':''}">${state.provider==='qq'?'平台暂不提供':value(p.history,' 条')}</span></div></section><div style="text-align:center;margin-top:25px">${button('取消整理','cancel','ghost')}</div>`; }
    function localDate(value) {
      const parsed = new Date(value);
      return Number.isNaN(parsed.getTime()) ? (value || '未知') : parsed.toLocaleString('zh-CN', {year:'numeric',month:'long',day:'numeric',hour:'2-digit',minute:'2-digit'});
    }
    function music() {
      if (!state.dashboard) return `${header('YOUR MUSIC','我的音乐','${isOnline?"当前会话整理完成后会在这里显示数据。":"已整理过的数据可离线恢复。"}')}<div class="card empty"><p>还没有音乐数据。连接一个平台，开始探索。</p>${button('选择音乐平台','explore','primary')}</div>`;
      const m = state.dashboard;
      const maxArtist = Math.max(1,...m.top_artists.map(row=>row.count));
      const artists = m.top_artists.length ? m.top_artists.map(row=>`<div class="chart-row"><span class="name" title="${esc(row.name)}">${esc(row.name)}</span><div class="chart-track"><div class="chart-fill" style="width:${Math.round(row.count/maxArtist*100)}%"></div></div><span class="count">${row.count}</span></div>`).join('') : '<p>暂无歌手数据。</p>';
      const albums = m.top_albums.length ? m.top_albums.map((row,i)=>`<div class="rank-row"><span>${String(i+1).padStart(2,'0')} · ${esc(row.name)}</span><span>${row.count} 首</span></div>`).join('') : '<p>暂无专辑数据。</p>';
      const sourceOptions = state.sources.map(row=>`<option value="${row.id}" ${row.id===state.source_id?'selected':''}>${esc(row.label)} · ${esc(localDate(row.updated_at))}</option>`).join('');
      const compare = m.platforms.length > 1 ? `<div class="section-head"><h3>两个平台，各自的数据</h3><p>数量来自各平台导出结果；跨平台重复歌曲只在总计中去重。</p></div><section class="card">${m.platforms.map(row=>`<div class="platform-row"><strong>${esc(row.name)}</strong><span>喜欢 ${row.liked} · 歌单 ${row.playlists} · 不同歌曲 ${row.unique}</span></div>`).join('')}</section>` : '';
      return `${toast()}${header('YOUR MUSIC','我的音乐','这些数字只陈述已获取的数据，不解释你的性格或喜好原因。')}
        <div class="data-toolbar"><div class="data-meta">${esc(m.source)} · 更新于 ${esc(localDate(m.updated_at))}${m.status==='partial'?' · 部分数据未能获取':''}</div>${state.sources.length>1?`<select id="source-select" class="source-select" aria-label="选择本地数据">${sourceOptions}</select>`:''}</div>
        <div class="metric-grid"><div class="metric"><strong>${m.liked}</strong><span>喜欢歌曲</span></div><div class="metric"><strong>${m.unique}</strong><span>不同歌曲</span></div><div class="metric"><strong>${m.artists}</strong><span>歌手</span></div><div class="metric"><strong>${m.playlists}</strong><span>歌单</span></div><div class="metric"><strong>${m.albums??0}</strong><span>专辑</span></div><div class="metric"><strong>${m.history??0}</strong><span>可用记录</span></div></div>
        <div class="insight-grid"><section class="card"><div class="eyebrow">TOP ARTISTS</div><h3>喜欢歌曲中常出现的歌手</h3><p>按喜欢歌曲中的出现次数统计。</p>${artists}</section><section class="card"><div class="eyebrow">TOP ALBUMS</div><h3>喜欢歌曲中常出现的专辑</h3><p>按喜欢歌曲中的出现次数统计。</p>${albums}</section></div>
        <section class="card"><h3>歌单规模</h3><div class="playlist-facts"><span><strong>${m.created_playlists}</strong>自建</span><span><strong>${m.subscribed_playlists}</strong>收藏</span><span><strong>${m.largest_playlist}</strong>最大歌单的歌曲数</span></div></section>
        <section class="card coverage"><h3>数据覆盖</h3><p>${m.status==="partial"?"部分内容不可获取；请查看导出中的问题列表。":"已完成当前可访问数据的整理。"} 网易云记录仅覆盖平台返回范围；QQ 音乐完整播放历史不可用。收藏顺序不能作为收藏日期。</p></section>${compare}<section class="card" style="margin-top:17px"><h3>搜索本地音乐</h3><p>按歌曲、歌手或专辑查找；只浏览数据，不播放或下载音乐。</p><input id="music-search" class="search-box" type="search" placeholder="搜索歌曲 / 歌手 / 专辑" aria-label="搜索本地音乐"><div id="search-results" class="search-results" aria-live="polite"></div></section><div class="feature-grid" style="margin-top:17px"><section class="card"><div class="eyebrow">NEXT STEP</div><h3>让 AI 帮你继续理解</h3><p>选择一个方向，直接在程序里查看并复制完整 Prompt。</p>${button('探索 AI 分析','go-ai','small')}</section><section class="card"><div class="eyebrow">YOUR FILES</div><h3>${isOnline?"数据临时保存在服务器":"数据保存在本机"}</h3><p>查看 JSON、摘要与分析指南；无需到文件夹里寻找提示词。</p>${button('浏览音乐档案','go-library','small')}${button('查看导出文件','go-export','small')}</section></div>`;
    }
    function ai() {
      if (!state.dashboard) return `${header('AI ANALYSIS','探索你的音乐世界','完成一次音乐整理后，分析方向会出现在这里。')}<div class="card empty"><p>还没有可供分析的音乐数据。</p>${button('先整理音乐数据','explore','primary')}</div>`;
      if (activeTopic) {
        const t = activeTopic;
        const scope = t.scope.split(/[、；]/).map(part=>part.trim()).filter(Boolean).map(part=>`<span>${esc(part)}</span>`).join('');
        return `<div class="topic-detail"><button class="topic-back" data-action="ai-back">← 返回分析方向</button><div class="eyebrow">ANALYSIS ${String(t.number).padStart(2,'0')}</div><h2>${esc(t.title)}</h2><p class="lead">${esc(t.question)}</p>${t.reason?`<div class="toast">${esc(t.reason)}</div>`:''}<div class="section-head"><h3>AI 会分析</h3><p>具体结论由你选择的 AI 根据上传文件给出。</p></div><div class="scope-list">${scope}</div><p class="small-note">联网：${esc(t.network)} · 分析深度：${esc(t.depth)}</p><div class="section-head"><h3>完整 Prompt</h3><p>这段文字可以独立使用，已包含数据范围与缺失说明。</p></div><textarea id="prompt-text" class="prompt-box" readonly aria-label="完整 AI Prompt">${esc(t.prompt)}</textarea><div class="copy-line">${button('复制 Prompt','copy-prompt','primary')}${button('下载 Prompt','download-prompt','small')}${isWeb?`<a class="btn small" href="${esc(API.fileURL(t.filename,state))}">下载数据文件</a>`:button('打开数据文件夹','open-folder','small')}<span class="copy-ok" role="status">${copied?'✓ 已复制':''}</span></div><section class="card"><h3>怎么使用？</h3><ol class="steps"><li>打开 ChatGPT、Claude、Gemini，或其他支持文件上传的 AI。</li><li>上传 <strong>${esc(t.filename)}</strong>。</li><li>点击“复制 Prompt”。</li><li>把 Prompt 粘贴给 AI。</li><li>开始分析，并让 AI 指出对应的歌曲或歌单证据。</li></ol><p class="small-note">上传前，请确认你愿意把个人音乐数据交给所选 AI 服务。</p></section></div>`;
      }
      const routes = [
        ['第一次使用','全景画像 → 真实音乐审美 → 核心歌手 → 音乐地图 → 系统听歌计划'],
        ['只想娱乐看看','全景画像 → 年度总结 → 音乐谈资'],
        ['认真培养品味','真实音乐审美 → 核心歌手 → 音乐地图 → 审美盲区 → 系统听歌计划']
      ];
      const cards = state.topics.map(t=>`<button class="topic-card" data-topic="${t.number}"><span class="topic-num">${String(t.number).padStart(2,'0')}</span><strong>${esc(t.title)}</strong><small>${esc(t.question)}</small><small>联网：${esc(t.network)} · ${esc(t.depth)}</small>${t.reason?`<span class="topic-note">数据有限，点击查看说明</span>`:''}</button>`).join('');
      return `${toast()}${header('AI ANALYSIS','探索你的音乐世界','请选择你感兴趣的方向。每个 Prompt 都能独立复制使用。')}<div class="route-grid">${routes.map(([title,description])=>`<div class="route-card"><h3>${title}</h3><p>${description}</p></div>`).join('')}</div><div class="section-head"><h3>分析方向</h3><p>Music Insight 负责整理数据和 Prompt；你自行选择 AI，无需 API Key。</p></div>${button("复制完整 AI 使用说明","copy-guide","small")}<div class="topic-grid">${cards}</div>`;
    }
    function exportPage() { if(!state.files.length)return `${header('YOUR FILES','导出 AI 数据')}<div class="card empty"><p>完成整理后可以下载音乐数据与 AI 指南。</p>${button('连接音乐平台','explore','primary')}</div>`; const rows=state.files.filter(f=>!f.name.startsWith('prompts/')&&!f.name.endsWith('.zip')).map(f=>`<div class="file-row"><div class="file-glyph">${f.name.endsWith('.json')?'AI':'MD'}</div><div class="file-description"><strong>${esc(f.name)}</strong><small>${esc(f.description)}</small></div>${isWeb?`<a class="btn small" href="${esc(API.fileURL(f.name,state))}">下载</a>`:''}</div>`).join(''); return `${toast()}${header('YOUR FILES','导出 AI 数据',isOnline?'文件来自当前会话的临时结果，请在会话结束前下载。':'文件已保存在本机输出目录。')}<div class="file-list">${rows}</div>${isOnline?`<a class="btn primary" href="${esc(API.fileURL('music-insight-export.zip',state))}">下载全部 · 含独立 Prompt</a>`:isWeb?button('下载全部 · 含独立 Prompt','download-all','primary'):button('打开数据文件夹','open-folder','primary')}<p class="small-note">单平台使用 music_for_ai.json，联合数据使用 music_for_ai_combined.json。</p>`; }
    function settings() { const s=state.settings; return `${toast()}${header('PREFERENCES','设置',isOnline?'无账号临时会话，退出后清除当前数据。':'设置保存在本机。')}<div class="settings-list">${isOnline?`<section class="settings-row"><h3>当前会话</h3><p>最多有效至 ${esc(localDate(state.session_expires_at*1000))}；结果也会按服务器设置到期清理。服务器重启后需重新扫码。</p>${button('退出并清除全部数据','logout','small')}${button('重新连接音乐平台','explore','small')}</section>`:`<section class="settings-row"><h3>输出位置</h3><div class="field-line"><input id="output-path" aria-label="输出路径" value="${esc(s.output_dir)}">${button('保存','save-folder','small')}${isWeb?'':button('选择文件夹','choose-folder','small')}</div></section>`}<section class="settings-row"><h3>外观</h3><div class="option-row">${[['dark','深色'],['light','浅色'],['system','跟随系统']].map(([id,name])=>`<button class="btn small ${s.theme===id?'active':''}" data-action="theme-${id}">${name}</button>`).join('')}</div></section><section class="settings-row"><h3>数据与维护</h3><p>重新获取需要联网，缓存不作为长期云端档案。</p><div class="option-row">${button('清除缓存','clear-cache','small')}${button('重新获取数据','explore','small')}${isOnline?'':button('打开日志目录','open-logs','small')}</div></section>${isWeb?'':`<section class="settings-row"><h3>Local Web</h3><p>在默认浏览器中打开本机版本。</p>${button('启动 Web 版','start-web','small')}</section>`}</div>`; }
    function errorPage() { const e=state.error || {title:'遇到问题',body:'请稍后重试。',detail:''}; return `${header('SOMETHING HAPPENED',esc(e.title),'整理没有完成，请检查连接后重试。')}<div class="flow-panel"><div class="error-accent">!</div><p>${esc(e.body)}</p><div class="flow-actions">${button('重试','retry','primary')}${button('返回选择','explore','ghost')}</div><details><summary>查看详细信息</summary><pre>${esc(e.detail)}</pre></details></div>`; }
    const pages = {library,cross,privacy,home,platforms,login,connected,progress,music,ai,export:exportPage,settings,error:errorPage};
    function render() {
      if (!state) return;
      if (lastFolder !== state.result_folder) { activeTopic=null; copied=false; lastFolder=state.result_folder; }
      document.documentElement.dataset.theme=state.settings.theme==='system'?(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'):state.settings.theme;
      document.getElementById('side-version').textContent=`VERSION ${state.version}`;
      document.getElementById('crumb').textContent=`MUSIC INSIGHT / ${labels[state.view] || '首页'}`;
      nav.innerHTML=navItems.filter(([id])=>id!=='cross'||state.data_filename==='music_for_ai_combined.json').map(([id,icon,label])=>`<button data-nav="${id}" class="${state.view===id?'active':''}" ${state.busy?'disabled':''}><span class="nav-icon" aria-hidden="true">${icon}</span>${label}</button>`).join('');
      content.innerHTML=trustedPageMarkup((pages[state.view] || home)()+'<footer class="product-footer">Music Insight 为非官方开源项目，与网易云音乐、QQ 音乐及其关联公司无官方关系。</footer>'); document.querySelector('.top-status').textContent=isOnline?'临时会话 · 隐私说明':'本机整理 · 私人空间'; if(state.view==='library')loadLibrary().catch(()=>{});if(state.view==='cross')loadCross().catch(()=>{});
      const qr=document.getElementById('qr-image'); if(qr) qr.src=state.qr;
    }
    async function poll() {
      if(!bridgeReady || polling || expired) return;
      polling=true;
      try {
        const update=await callCore('snapshot',revision);
        if(update.state) { revision=update.revision; state=update.state; render(); }
      } catch(error) { document.getElementById('crumb').textContent='MUSIC INSIGHT / 连接中'; }
      finally { polling=false; }
    }
    async function invoke(name,...args) {
      try {
        const result=await callCore(name,...args);
        if(result && result.ok===false && !result.cancelled && result.message) alert(result.message);
        await poll();
        return result;
      } catch(error) { alert(error.message||'操作暂时无法完成，请重试。'); return {ok:false}; }
    }
    async function openTopic(number) {
      const result=await invoke('get_topic',number);
      if(result && result.ok) { activeTopic=result.topic; copied=false; render(); document.querySelector('.main').scrollTop=0; }
    }
    document.addEventListener('click',async event=>{
      const node=event.target.closest('[data-action],[data-nav],[data-topic]');
      if(!node || !bridgeReady) return;
      if(node.dataset.nav) { activeTopic=null; invoke('navigate',node.dataset.nav); return; }
      if(node.dataset.topic) { await openTopic(Number(node.dataset.topic)); return; }
      const action=node.dataset.action;
      if(action==='explore'||action.startsWith('go-')) {
        if(action==='go-ai') activeTopic=null;
        if(expired){expired=false;revision=-1;await callCore('snapshot',-1);await poll();} invoke('navigate',action==='explore'?'platforms':action.slice(3));
      } else if(action.startsWith('start-')&&action!=='start-web') {if(isOnline&&!document.getElementById('online-consent')?.checked){alert('请先阅读并同意临时处理数据的隐私说明。');return;} invoke('start',action.slice(6));}
      else if(action==='begin') invoke('begin_export');
      else if(action==='refresh') invoke('refresh_qr');
      else if(action==='cancel') invoke('cancel');
      else if(action==='retry') { if(isOnline)invoke('navigate','platforms');else invoke('start',state.selected); }
      else if(action==='open-folder') invoke('open_result_folder');
      else if(action==='open-logs') invoke('open_logs');
      else if(action==='start-web') invoke('start_web');
      else if(action==='theme-dark'||action==='theme-light'||action==='theme-system') invoke('set_theme',action.slice(6));
      else if(action==='save-folder') invoke('set_output_dir',document.getElementById('output-path').value);
      else if(action==='choose-folder') invoke('choose_output_dir');
      else if(action==='fresh') { if(state.selected) invoke('start',state.selected,true); else invoke('navigate','platforms'); }
      else if(action==='clear-cache') { if(confirm('清除近期缓存？已导出的文件不会删除。')) invoke('clear_cache'); }
      else if(action==='ai-back') { activeTopic=null; copied=false; render(); }
      else if(action==='copy-prompt' && activeTopic) {
        if(isWeb) {
          try { await navigator.clipboard.writeText(activeTopic.prompt); copied=true; render(); }
          catch(error) { alert('复制失败，请手动选择上方文字。'); }
        } else {
          const result=await invoke('copy_prompt',activeTopic.number);
          if(result && result.ok) { copied=true; render(); }
        }
      }
    });
    document.addEventListener('change',event=>{
      if(event.target.id==='source-select') {
        activeTopic=null; copied=false;
        API.selectSource(event.target.value).then(poll);
      }
    });
    document.addEventListener('input',event=>{
      if(event.target.id!=='music-search' || !bridgeReady) return;
      clearTimeout(searchTimer);
      const input=event.target, query=input.value.trim(), holder=document.getElementById('search-results');
      if(!query) { holder.innerHTML=''; return; }
      searchTimer=setTimeout(async()=>{
        try {
          const result=await callCore('search_catalog',query);
          if(!holder.isConnected || input.value.trim()!==query) return;
          const rows=result.results || [];
          holder.innerHTML=rows.length ? rows.map(row=>`<div class="search-row"><span>${esc(row.name)}</span><span>${esc(row.artists)}${row.album?' · '+esc(row.album):''}</span></div>`).join('') : '<p class="small-note">没有找到匹配的本地歌曲。</p>';
        } catch(error) { if(holder.isConnected) holder.innerHTML='<p class="small-note">搜索暂时不可用。</p>'; }
      },180);
    });
    window.addEventListener('pywebviewready',()=>{ bridgeReady=true; poll(); setInterval(poll,350); });
    if(isWeb) { bridgeReady=true; poll(); setInterval(poll,isOnline?700:500); }

matchMedia('(prefers-color-scheme: light)').addEventListener('change',()=>{if(state?.settings.theme==='system')render();});
