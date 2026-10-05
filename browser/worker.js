import { loadPyodide } from './runtime/pyodide.mjs';

const base = new URL('.', import.meta.url);
const resourceNames = new Set([
  'core.json', 'demo.json', 'runtime/pyodide.asm.mjs', 'runtime/pyodide.asm.wasm',
  'runtime/pyodide-lock.json', 'runtime/python_stdlib.zip',
]);
const networkFetch = globalThis.fetch.bind(globalThis);
// Only fixed, same-origin code/demo assets can be fetched by the worker.
// Imported music never appears in a URL, body, header, or network request.
globalThis.fetch = (input, options = {}) => {
  const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url, base);
  const name = url.pathname.slice(base.pathname.length);
  if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname) ||
      !resourceNames.has(name) || url.search || url.hash || options.body ||
      (options.method && options.method !== 'GET')) {
    return Promise.reject(new Error('Only fixed application assets are permitted'));
  }
  return networkFetch(url, { ...options, credentials: 'omit', referrerPolicy: 'no-referrer' });
};

let runtimePromise;
function runtime() {
  if (!runtimePromise) runtimePromise = (async () => {
    postMessage({ status: '正在准备浏览器运行环境，首次打开可能需要稍等片刻…' });
    const python = await loadPyodide({ indexURL: new URL('runtime/', base).href,
      stdout: () => {}, stderr: () => {} });
    const response = await fetch(new URL('core.json', base));
    if (!response.ok) throw new Error('Application assets unavailable');
    const files = await response.json();
    for (const [name, text] of Object.entries(files)) {
      if (!/^[a-z_/]+\.py$/.test(name) || name.includes('..')) throw new Error('Invalid Core path');
      const path = `/app/netease_music_insight/${name}`;
      python.FS.mkdirTree(path.slice(0, path.lastIndexOf('/')));
      python.FS.writeFile(path, text, { encoding: 'utf8' });
    }
    python.runPython(`
import sys, json
sys.path.insert(0, '/app')
from netease_music_insight.browser import BrowserSession, BrowserInputError
_browser_session = BrowserSession()
def _browser_call(payload):
    handlers = {name: getattr(_browser_session, name) for name in (
        'prepare', 'discard', 'commit', 'snapshot', 'select', 'topic', 'search', 'download', 'clear', 'demo')}
    try:
        request = json.loads(payload)
        result = handlers[request['method']](*request.get('args', []))
        return json.dumps({'ok': True, 'result': result}, ensure_ascii=False)
    except BrowserInputError as error:
        return json.dumps({'ok': False, 'message': str(error)}, ensure_ascii=False)
    except Exception:
        return json.dumps({'ok': False, 'message': '暂时无法处理这个文件。请使用 Music Insight 导出的完整 JSON，或重新打开页面后再试。'}, ensure_ascii=False)
`);
    return python;
  })();
  return runtimePromise;
}

let queue = Promise.resolve();
async function handle(message) {
  const { id, method } = message;
  try {
    const python = await runtime();
    let args = message.args || [];
    if (method === 'prepare') args = [message.buffers.map(buffer => new TextDecoder('utf-8', { fatal: true }).decode(buffer))];
    if (method === 'demo') {
      const response = await fetch(new URL('demo.json', base));
      if (!response.ok) throw new Error('Demo unavailable');
      args = [(await response.json()).map(value => JSON.stringify(value))];
    }
    python.globals.set('_browser_payload', JSON.stringify({ method, args }));
    let result;
    try { result = JSON.parse(python.runPython('_browser_call(_browser_payload)')); }
    finally { python.globals.delete('_browser_payload'); }
    postMessage({ id, ...result });
  } catch {
    runtimePromise = null;
    postMessage({ id, ok: false, message: '浏览器运行环境未能加载，或文件不是 UTF-8 编码。请检查网络后重试，并选择 Music Insight 导出的 JSON。' });
  }
}
self.onmessage = event => { queue = queue.then(() => handle(event.data)); };
