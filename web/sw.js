// Forge service worker — push + offline shell (AppFlow Flow 2/3, Design §7).
const CACHE = "forge-v2";
const SHELL = [
  "./",
  "index.html",
  "app.js",
  "manifest.webmanifest",
  "vendor/marked.min.js",
  "vendor/purify.min.js",
  "vendor/jspdf.umd.min.js",
  "icons/icon-180.png",
  "icons/icon-192.png",
  "icons/icon-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => clients.claim())
  );
});

// cache-first for the same-origin shell; API calls (other origin) go straight to network
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(
      (hit) =>
        hit ||
        fetch(e.request).then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
          return res;
        })
    )
  );
});

self.addEventListener("push", (e) => {
  let d = { title: "Forge", body: "Check in." };
  try {
    d = e.data.json();
  } catch (_) {
    /* keep default */
  }
  // plain text only, length-capped — LLM output is untrusted (Security §6)
  const title = String(d.title || "Forge").slice(0, 60);
  const body = String(d.body || "").slice(0, 240);
  e.waitUntil(self.registration.showNotification(title, { body }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  e.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((ws) => (ws.length ? ws[0].focus() : clients.openWindow("./")))
  );
});
