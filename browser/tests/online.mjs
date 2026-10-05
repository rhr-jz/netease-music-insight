// Shared UI integration against scripts/online_ui_fixture.py (real Core, fake accounts).
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';

const base=process.env.MUSIC_ONLINE_TEST_URL||'http://127.0.0.1:58003';
const browser=await chromium.launch({headless:true,...(process.env.MUSIC_BROWSER_CHANNEL?{channel:process.env.MUSIC_BROWSER_CHANNEL}:{})});
const context=await browser.newContext({viewport:{width:1280,height:900},permissions:['clipboard-read','clipboard-write']});
const page=await context.newPage();const errors=[],csp=[],outbound=[];
page.on('pageerror',e=>errors.push(String(e)));
page.on('console',m=>{if(m.text().includes('Content Security Policy'))csp.push(m.text());});
page.on('request',r=>{if(!r.url().startsWith(base))outbound.push(r.url());});
page.on('dialog',d=>d.accept());
await mkdir('build/online/screenshots',{recursive:true});let checks=0;
const pass=s=>{checks++;console.log('PASS '+s);};
const nav=async id=>{await page.locator(`[data-nav="${id}"]`).click();};
const action=async id=>{await page.locator(`[data-action="${id}"]`).first().click();};
async function connect(provider){
  await nav('home');
  await action('explore');await page.locator('#online-consent').check();await action('start-'+provider);
  await page.locator('#qr-image').waitFor();assert.ok((await page.locator('#qr-image').getAttribute('src')).startsWith('data:image/png'));
  await page.screenshot({path:'build/online/screenshots/qr-demo.png'});
  await page.locator('[data-action="begin"]').waitFor();await action('begin');
  await page.getByRole('heading',{name:'我的音乐',exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelector('[data-nav="settings"]')&&!document.querySelector('[data-nav="settings"]').disabled);
}
try{
  await page.goto(base);await page.getByRole('heading',{name:'听见自己。'}).waitFor();
  await page.screenshot({path:'build/online/screenshots/home.png'});pass('landing and anonymous session');
  await nav('music');await page.getByText('还没有音乐数据。',{exact:false}).waitFor();pass('friendly empty state');
  await connect('netease');assert.equal(await page.locator('.metric strong').first().textContent(),'85');pass('NetEase QR, begin and export');
  await page.reload();await page.getByRole('heading',{name:'我的音乐',exact:true}).waitFor();pass('refresh restores session');
  await nav('library');await page.locator('.library-row').first().waitFor();assert.equal(await page.locator('.library-row').count(),40);
  await action('library-next');await page.getByText('2 / 3',{exact:true}).waitFor();pass('pagination limits DOM');
  await action('library-playlists');await page.locator('[data-playlist]').first().click();await page.getByText('演示歌单 · 85 条',{exact:false}).waitFor();pass('playlist details');
  await page.locator('#library-search').fill('歌-84');await page.waitForFunction(()=>document.querySelectorAll('.library-row').length===1);pass('search metadata');
  await connect('all');await page.locator('#source-select').waitFor();assert.equal(await page.locator('#source-select').inputValue(),'combined');
  await nav('cross');await page.getByText('共同录音',{exact:true}).waitFor();pass('Combined comparison');
  await nav('ai');await page.locator('[data-topic]').first().waitFor();assert.equal(await page.locator('[data-topic]').count(),13);
  for(let n=1;n<=13;n++){
    await page.locator(`[data-topic="${n}"]`).click();await page.locator('#prompt-text').waitFor();
    const prompt=await page.locator('#prompt-text').inputValue();assert.ok(prompt.includes('music_for_ai_combined.json'));
    await action('copy-prompt');await page.getByText('✓ 已复制',{exact:true}).waitFor();assert.equal((await page.evaluate(()=>navigator.clipboard.readText())).replace(/\r\n/g,'\n'),prompt);
    await action('ai-back');
  }pass('all 13 complete prompts and clipboard');
  await action('copy-guide');await page.getByText('✓ 已复制完整 AI 使用说明',{exact:true}).waitFor();pass('full guide clipboard');
  await page.locator('[data-topic="2"]').click();await page.locator('#prompt-text').waitFor();
  const promptDownload=page.waitForEvent('download');await action('download-prompt');assert.ok((await promptDownload).suggestedFilename().endsWith('.md'));pass('individual prompt download');
  await nav('export');const zip=page.waitForEvent('download');await page.getByRole('link',{name:'下载全部 · 含独立 Prompt'}).click();assert.equal((await zip).suggestedFilename(),'music-insight-export.zip');pass('ZIP download');
  for(const width of [390,430,768,1280,1920]){
    await page.setViewportSize({width,height:900});for(const id of ['home','platforms','music','library','ai','export','privacy','settings']){
      if(id==='platforms')await action('explore');else await nav(id);await page.waitForTimeout(100);
      const sizes=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth}));assert.ok(sizes.scroll<=sizes.width+1,`${id} at ${width} overflows: ${JSON.stringify(sizes)}`);
    }
  }pass('responsive layouts at 390/430/768/1280/1920');
  await page.setViewportSize({width:1280,height:900});await nav('settings');await action('theme-light');await page.waitForFunction(()=>document.documentElement.dataset.theme==='light');await action('theme-system');pass('light/dark/system theme');
  const second=await browser.newContext();const other=await second.newPage();await other.goto(base);await other.getByRole('heading',{name:'听见自己。'}).waitFor();await other.locator('[data-nav="music"]').click();await other.getByText('还没有音乐数据。',{exact:false}).waitFor();await second.close();pass('separate browser context has no private result');
  const fallback=await browser.newContext();await fallback.route('**/api/events',r=>r.abort());const fp=await fallback.newPage();await fp.goto(base);await fp.getByRole('heading',{name:'听见自己。'}).waitFor();await fp.locator('[data-nav="privacy"]').click();await fp.getByRole('heading',{name:'你的音乐，属于你。'}).waitFor();await fallback.close();pass('SSE failure falls back to polling');
  await nav('settings');await action('logout');await page.getByText('会话已结束，临时数据已清理。',{exact:false}).waitFor();await action('explore');await page.locator('#online-consent').waitFor();pass('logout and new session');
  assert.deepEqual(errors,[]);assert.deepEqual(csp,[]);assert.deepEqual(outbound,[]);pass('no script errors, CSP violations or third-party requests');
  console.log(`Online browser: ${checks} groups passed`);
}finally{await browser.close();}
