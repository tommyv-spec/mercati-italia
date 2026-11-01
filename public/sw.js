// The old Leaflet app registered a service worker at /sw.js and checks it for updates.
// This app has none: this file replaces it once, clears its caches and removes itself.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.map((name) => caches.delete(name))))
      .then(() => self.registration.unregister())
  );
});
