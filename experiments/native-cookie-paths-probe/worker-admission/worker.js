const entry = new URL('entry', self.registration.scope);
const cacheName = 'worker-admission-trap';
const document =
  '<!doctype html><title>c09-worker</title>' +
  "<script>window.workerTrap=true;window.workerProbeResult={source:'worker',scopes:[]};</script>";

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(cacheName);
      await cache.put(
        entry,
        new Response(document, { headers: { 'Content-Type': 'text/html; charset=utf-8' } }),
      );
      await self.skipWaiting();
    })(),
  );
});
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate' && event.request.url === entry.href) {
    event.respondWith(caches.match(entry, { cacheName }));
  }
});
