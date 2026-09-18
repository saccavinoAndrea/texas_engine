const CACHE_NAME = "texas-engine-shell";
const APP_SHELL = [
  "/",
  "/index.html",
  "/styles.css",
  "/app.js",
  "/manifest.json",
  "/icons/icon.svg",
  "/vendor/bootstrap/css/bootstrap.min.css",
  "/vendor/bootstrap/js/bootstrap.bundle.min.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

// Network-first: quando sei online prende sempre l'ultima versione dal server
// (nessun bisogno di aggiornare manualmente la cache ad ogni modifica del frontend).
// La cache serve solo come fallback se la rete non risponde (es. offline al tavolo).
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Le chiamate API sono sempre dinamiche: mai servite dalla cache.
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const responseClone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
