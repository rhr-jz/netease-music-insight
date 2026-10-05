const CACHE_PREFIX = 'music-insight-browser-';
const CACHE_NAME = CACHE_PREFIX + '__BUILD_ID__';
const scope = new URL('./', self.location.href);
let allowedPromise;
async function allowed() {
  if (!allowedPromise) allowedPromise = (async () => {
    const cache = await caches.open(CACHE_NAME);
    const response = await cache.match(new URL('precache.json', scope));
    if (!response) return new Set();
    const manifest = await response.json();
    return new Set(manifest.files.concat(['precache.json']).map(name => new URL(name, scope).href));
  })();
  return allowedPromise;
}
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const response = await fetch(new URL('precache.json', scope), { cache: 'no-store', credentials: 'omit' });
    if (!response.ok) throw new Error('Offline manifest unavailable');
    const manifest = await response.clone().json();
    if (!manifest.files.every(name => /^[a-zA-Z0-9_./-]+$/.test(name) && !name.includes('..') && !name.startsWith('/'))) throw new Error('Invalid offline asset path');
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(manifest.files.map(name => new Request(new URL(name, scope), { credentials: 'omit' })));
    await cache.put(new URL('precache.json', scope), response);
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME) await caches.delete(key);
    await self.clients.claim();
    for (const client of await self.clients.matchAll()) client.postMessage('offline-ready');
  })());
});
self.addEventListener('message', event => {
  if (event.data === 'offline-status') event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    if (await cache.match(new URL('precache.json', scope))) event.source?.postMessage('offline-ready');
  })());
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== scope.origin || url.search) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    const key = url.pathname === scope.pathname ? new URL('index.html', scope).href : url.href;
    if (!(await allowed()).has(key)) return fetch(request);
    return (await cache.match(key)) || fetch(request);
  })());
});
