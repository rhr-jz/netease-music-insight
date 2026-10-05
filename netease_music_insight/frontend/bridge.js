'use strict';
(() => {
  const online = document.querySelector('meta[name="music-insight-mode"]')?.content === 'online';
  const local = Boolean(window.musicInsightWeb);
  let initial = true, events = null, cached = null, healthy = false;
  async function request(path, body) {
    const response = await fetch(path, {method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',
      headers:body===undefined?{}:{'Content-Type':'application/json','X-Music-Insight-Request':'1'},
      ...(body===undefined?{}:{body:JSON.stringify(body)})});
    if(response.status===401){const e=new Error('会话已结束，请重新开始。');e.expired=true;throw e;}
    const value=await response.json();if(!response.ok)throw new Error(value.message||'操作暂时无法完成。');return value;
  }
  function subscribe(){if(events||!window.EventSource)return;events=new EventSource('/api/events');events.onmessage=e=>{cached=JSON.parse(e.data);healthy=true;};events.onerror=()=>{healthy=false;events.close();events=null;};events.addEventListener('expired',()=>{events.close();events=null;cached=null;healthy=false;initial=true;window.dispatchEvent(new Event('music-insight-expired'));});}
  async function call(method,...args){
    if(!online&&!local)return window.pywebview.api[method](...args);
    if(local){const r=await fetch('/api/call',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Music-Insight-CSRF':window.musicInsightWeb.csrf},body:JSON.stringify({method,args})});if(!r.ok)throw new Error('操作没有完成，请重试。');return r.json();}
    try{
      if(method==='snapshot'){
        if(healthy&&cached)return cached.revision===args[0]?{revision:args[0]}:cached;
        let result;try{result=await request('/api/snapshot?since='+Number(args[0]??-1));}catch(e){if(!initial||!e.expired)throw e;await request('/api/session',{});result=await request('/api/snapshot');}
        initial=false;subscribe();return result;
      }
      if(method==='start')return await request('/api/jobs',{provider:args[0],fresh:Boolean(args[1]),consent:Boolean(document.getElementById('online-consent')?.checked)});
      if(method==='browse_library')return await request('/api/library',{kind:args[0]||'catalog',query:args[1]||'',page:args[2]||1,playlist_id:args[3]||null});
      if(method==='search_catalog'){const r=await request('/api/library',{query:args[0]||''});return r;}
      if(method==='get_topic')return await request('/api/topics/'+Number(args[0]));
      if(method==='get_comparison')return await request('/api/comparison');
      if(method==='get_guide')return await request('/api/guide');
      if(method==='logout'){await request('/api/logout',{});events?.close();events=null;cached=null;healthy=false;initial=true;return{ok:true};}
      return await request('/api/actions',{method,args});
    }catch(e){if(e.expired){initial=true;window.dispatchEvent(new Event('music-insight-expired'));}throw e;}
  }
  window.MusicInsightAPI={mode:online?'online':local?'local':'desktop',call,
    snapshot:since=>call('snapshot',since),selectSource:id=>call('select_source',online?id:Number(id)),
    startLogin:(provider,fresh=false)=>call('start',provider,fresh),refreshQr:()=>call('refresh_qr'),
    beginExport:()=>call('begin_export'),cancel:()=>call('cancel'),searchCatalog:(q,page=1)=>call('browse_library','catalog',q,page),
    getTopic:n=>call('get_topic',n),clearCache:()=>call('clear_cache'),logout:()=>call('logout'),
    fileURL:(name,state)=>online?'/api/download/'+encodeURIComponent(state.files.find(f=>f.name===name)?.id||'missing'):'/download/'+encodeURIComponent(name)};
})();
