const { run, base, entry } = self.c09Config;
const entryUrl = new URL('/worker/entry', self.location.href);
const cacheName = 'c09-owned-entry';
self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(cacheName);
      await cache.put(
        entryUrl,
        new Response(entry, {
          headers: { 'Content-Type': 'text/html; charset=utf-8' },
        }),
      );
      await self.skipWaiting();
    })(),
  );
});
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate' && event.request.url === entryUrl.href) {
    event.respondWith(caches.match(entryUrl, { cacheName }));
  }
});
self.addEventListener('message', (event) => {
  const stage = event.data;
  if (!['worker-control', 'worker-blocked'].includes(stage) || !event.ports[0]) {
    return;
  }
  const query = new URLSearchParams({ run, case: stage });
  event.waitUntil(
    fetch(`${base}/worker-network?${query}`, { mode: 'no-cors', credentials: 'omit' }).then(
      () => event.ports[0].postMessage('reached'),
      () => event.ports[0].postMessage('blocked'),
    ),
  );
});
