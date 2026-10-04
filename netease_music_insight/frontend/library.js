'use strict';
function library() {
  if(!state.dashboard)return `${header('MUSIC ARCHIVE','音乐档案')}<section class="card empty">先连接音乐平台，整理自己的收藏。</section>`;
  return `${header('MUSIC ARCHIVE','音乐档案','浏览已整理的元数据，不播放或下载歌曲。')}<div class="option-row">${[['catalog','全部歌曲'],['liked','喜欢歌曲'],['playlists','歌单'],['history','播放记录']].map(([id,name])=>button(name,'library-'+id,libraryKind===id?'small active':'small')).join('')}</div><input class="search-box" id="library-search" type="search" placeholder="搜索歌曲 / 歌手 / 专辑" aria-label="搜索音乐档案" value="${esc(libraryQuery)}"><p id="library-description" class="small-note"></p><div id="library-rows" aria-live="polite">正在读取…</div><div id="library-pages" class="option-row"></div>`;
}
async function loadLibrary() {
  const serial=++librarySerial;
  const result=await callCore('browse_library',libraryKind,libraryQuery,libraryPage,playlistId);
  if(serial!==librarySerial||state.view!=='library')return;
  libraryPage=result.page;
  document.getElementById('library-description').textContent=`${result.title||''} · ${result.total} 条 · ${result.reason||'每页最多 40 条'}`;
  document.getElementById('library-rows').innerHTML=result.results.length?result.results.map(row=>libraryKind==='playlists'?`<button class="library-row playlist-link" data-playlist="${esc(row.id)}"><strong>${esc(row.name)}</strong><span>${esc(row.provider==='netease'?'网易云':'QQ 音乐')} · ${row.owned?'自建':'收藏'} · 已获取 ${row.count} 首 / 平台标记 ${row.expected??'未知'} 首</span><small>${row.created_at?'创建时间：'+esc(localDate(row.created_at)):row.subscribed_at?'收藏时间：'+esc(localDate(row.subscribed_at)):row.favorite_order_at?'收藏排序时间：'+esc(localDate(row.favorite_order_at)):'时间不可用'}</small></button>`:`<div class="library-row"><strong>${esc(row.name)}</strong><span>${esc(row.artists)} · ${esc(row.album)}</span><small>${row.provider==='netease'?'网易云':'QQ 音乐'} · ${row.liked?'喜欢歌曲':'未标记喜欢'} · ${esc((row.playlists||[]).join(' / ')||'无歌单归属')}${row.play_count!=null?' · 平台返回播放次数 '+row.play_count:''}${row.liked_at?' · 收藏时间 '+esc(localDate(row.liked_at)):''}${row.added_at?' · 加入时间 '+esc(localDate(row.added_at)):''}</small></div>`).join(''):'<section class="card empty">没有可显示的数据。</section>';
  document.getElementById('library-pages').innerHTML=`<button class="btn small" data-action="library-prev" ${result.page<=1?'disabled':''}>上一页</button><span>${result.page} / ${result.pages}</span><button class="btn small" data-action="library-next" ${result.page>=result.pages?'disabled':''}>下一页</button>`;
}
function cross(){return `${header('TWO WORLDS','跨平台音乐档案','标题、歌手与时长一致且匹配唯一时才合并。')}<div id="cross-content">正在读取…</div>`;}
async function loadCross(){
  const {comparison:c}=await callCore('get_comparison');if(state.view!=='cross')return;
  document.getElementById('cross-content').innerHTML=c?`<div class="metric-grid">${[[c.common_tracks,'共同录音'],[c.netease_only,'网易云独有'],[c.qq_only,'QQ 音乐独有'],[c.common_artists_count,'共同歌手']].map(([n,label])=>`<div class="metric"><strong>${n}</strong><span>${label}</span></div>`).join('')}</div><div class="insight-grid"><section class="card"><h3>共同歌曲 · 示例</h3>${c.sample_common.map(r=>`<p>${esc(r.name)} · ${esc(r.artists)}</p>`).join('')||'<p>没有高置信匹配。</p>'}</section><section class="card"><h3>共同歌手</h3><p>${esc(c.common_artists.join(' / ')||'暂无')}</p><h3>网易云独有歌手 · 示例</h3><p>${esc(c.netease_only_artists.join(' / ')||'暂无')}</p><h3>QQ 音乐独有歌手 · 示例</h3><p>${esc(c.qq_only_artists.join(' / ')||'暂无')}</p></section></div><section class="card"><h3>歌单结构</h3>${c.playlists.map(p=>`<p>${p.provider==='netease'?'网易云':'QQ 音乐'}：自建 ${p.created} · 收藏 ${p.subscribed}</p>`).join('')}</section>`:'<section class="card empty">完成两个平台的联合整理后可以比较。</section>';
}
function privacy(){return `${header('PRIVACY','你的音乐，属于你。')}<div class="insight-grid"><section class="card"><h3>Desktop / Local Web</h3><p>平台凭据和音乐数据保存在自己的电脑。Local Web 仅监听 127.0.0.1。直接向音乐平台请求数据。</p></section><section class="card"><h3>Online Web</h3><p>为完成扫码和整理，部署服务器会临时处理平台凭据、账号资料和音乐元数据。凭据保留在后端，浏览器不会获得平台 Cookie。</p><p>会话和结果默认最多 1 小时；退出会立即撤销访问、清除凭据，并取消正在运行的任务。等待中的网络请求返回后，临时文件完成删除。已下载的数据由你自行保管。</p></section></div><section class="card"><h3>透明的数据边界</h3><p>不索取密码、不建立云端用户档案、不接广告或统计 SDK、不自动向 AI 发送数据。技术日志仅记录阶段与错误类别。部署者的网络服务商、反向代理与音乐平台可能处理网络信息，应查看实际网站的隐私政策。</p><p>QQ 音乐不提供可靠完整播放历史；网易云记录范围有限。收藏顺序不等于收藏日期，歌单收藏不代表每首歌都听过。</p><p>上传给 ChatGPT、Claude、Gemini 等 AI 是你独立选择的操作，请先确认其隐私政策。</p></section>`;}
function applyTrustedStyles(){
  const nonce=document.querySelector('meta[name="style-nonce"]')?.content;if(!nonce)return;
  document.getElementById('dynamic-layout')?.remove();
  const rules=[];content.querySelectorAll('[style]').forEach((node,index)=>{
    const authorStyle=node.getAttribute('style');node.removeAttribute('style');
    // Only layout declarations authored by this UI; no user-controlled CSS.
    if(!/^(?:(?:width|margin|margin-top|text-align|font-size):[\d\s.%pxa-z-]+;?)+$/.test(authorStyle))return;
    const name='layout-'+index;node.classList.add(name);rules.push('.'+name+'{'+authorStyle+'}');
  });
  const sheet=document.createElement('style');sheet.id='dynamic-layout';sheet.nonce=nonce;sheet.textContent=rules.join('\n');document.head.append(sheet);
}
function trustedPageMarkup(markup){
  const nonce=document.querySelector('meta[name="style-nonce"]')?.content;if(!nonce)return markup;
  document.getElementById('dynamic-layout')?.remove();const rules=[];
  const safe=markup.replace(/<([a-z][a-z0-9-]*)([^<>]*)>/gi,(tag,name,attrs)=>{
    const match=attrs.match(/\sstyle="([^"]*)"/);if(!match)return tag;
    attrs=attrs.replace(match[0],'');const style=match[1];
    if(!/^(?:(?:width|margin|margin-top|text-align|font-size):[\d\s.%pxa-z-]+;?)+$/.test(style))return '<'+name+attrs+'>';
    const cls='layout-'+rules.length;rules.push('.'+cls+'{'+style+'}');
    attrs=/\sclass="/.test(attrs)?attrs.replace(/class="([^"]*)"/,(_,value)=>'class="'+value+' '+cls+'"'):attrs+' class="'+cls+'"';
    return '<'+name+attrs+'>';
  });
  const sheet=document.createElement('style');sheet.id='dynamic-layout';sheet.nonce=nonce;sheet.textContent=rules.join('\n');document.head.append(sheet);return safe;
}
window.addEventListener('music-insight-expired',()=>{expired=true;activeTopic=null;copied=false;revision=-1;if(state){state.view='home';state.busy=false;state.qr=null;state.nickname='';state.dashboard=null;state.files=[];state.sources=[];state.topics=[];state.result_folder='';render();}});
document.addEventListener('change',event=>{if(event.target.id==='online-consent')consent=event.target.checked;});
document.addEventListener('input',event=>{if(event.target.id==='library-search'){libraryQuery=event.target.value;libraryPage=1;clearTimeout(searchTimer);searchTimer=setTimeout(()=>loadLibrary().catch(()=>{}),180);}});
document.addEventListener('click',async event=>{
  const node=event.target.closest('[data-action],[data-playlist]');if(!node||!bridgeReady)return;
  if(node.dataset.playlist){playlistId=node.dataset.playlist;libraryKind='playlist';libraryPage=1;render();return;}
  const action=node.dataset.action;
  if(action?.startsWith('library-')){const kind=action.slice(8);if(kind==='prev')libraryPage--;else if(kind==='next')libraryPage++;else{libraryKind=kind;libraryPage=1;playlistId=null;}await loadLibrary();}
  else if(action==='logout'){await API.logout();window.dispatchEvent(new Event('music-insight-expired'));}
  else if(action==='save-qr'&&state.qr){downloadBlob(state.qr,'music-insight-qr.png');}
  else if(action==='download-all'){const result=await invoke('prepare_archive');if(result.ok)downloadBlob(API.fileURL(result.name,state),result.name);}
  else if(action==='download-prompt'&&activeTopic){const url=URL.createObjectURL(new Blob([activeTopic.prompt],{type:'text/markdown;charset=utf-8'}));downloadBlob(url,'music-insight-prompt-'+activeTopic.number+'.md');setTimeout(()=>URL.revokeObjectURL(url),1000);}
  else if(action==='copy-guide'){const result=await invoke('get_guide');if(result.ok){if(isWeb){await navigator.clipboard.writeText(result.text);state.toast='✓ 已复制完整 AI 使用说明';render();}else{await invoke('copy_guide');}}}
});
function downloadBlob(url,name){const a=document.createElement('a');a.href=url;a.download=name;a.click();}
