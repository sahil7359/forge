self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(clients.claim()));

self.addEventListener("push", (e) => {
  let d = { title: "Forge", body: "Check in." };
  try { d = e.data.json(); } catch (_) { /* keep default */ }
  e.waitUntil(self.registration.showNotification(d.title || "Forge", { body: d.body || "" }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  e.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((ws) =>
      ws.length ? ws[0].focus() : clients.openWindow("./")
    )
  );
});

// TODO P3: offline shell cache (cache-first for ./, app.js, vendor/*) per AppFlow Flow 2.
