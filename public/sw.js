// The old Leaflet app registered a service worker at /sw.js and checks it for updates.
// This app has none: this file replaces it once, clears its caches, removes itself and
// reloads any page still open on the old app, so it moves to this one without asking.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    await Promise.all((await caches.keys()).map((name) => caches.delete(name)));
    await self.clients.claim();
    const pages = await self.clients.matchAll({ type: 'window' });
    await self.registration.unregister();
    await Promise.all(pages.map((page) => page.navigate(page.url).catch(() => {})));
  })());
});
