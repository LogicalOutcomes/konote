// KoNote — Minimal service worker for offline fallback only.
// NOT a full PWA — only caches the offline page.
var CACHE_NAME = "konote-offline-v2";
var OFFLINE_URL = "/static/offline.html";

self.addEventListener("install", function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.add(OFFLINE_URL);
        })
    );
    self.skipWaiting();
});

self.addEventListener("activate", function(event) {
    event.waitUntil(
        caches.keys().then(function(names) {
            return Promise.all(
                names.filter(function(n) { return n !== CACHE_NAME; })
                     .map(function(n) { return caches.delete(n); })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener("fetch", function(event) {
    // Only intercept navigation requests (full page loads)
    if (event.request.mode !== "navigate") return;

    event.respondWith(
        fetch(event.request).catch(function() {
            // Only show offline page when actually offline.
            // Back-button navigations can fail due to Vary header
            // mismatches (HTMX adds Vary: HX-Request) — these are
            // not real offline events and should not show offline.html.
            if (!self.navigator.onLine) {
                return caches.match(OFFLINE_URL);
            }
            // Not offline — let the browser show its own error page
            // (e.g. back/forward cache miss or transient network blip)
            return Response.error();
        })
    );
});
