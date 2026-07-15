// Forge PWA — S1 shell. Full app logic lands in P3 (docs/Design.md, docs/AppFlow.md).
const CONFIG = {
  API_BASE: "https://YOUR-SERVICE.onrender.com", // TODO P0: real Render URL
  VAPID_PUBLIC_KEY: "PASTE_VAPID_PUBLIC_KEY",    // TODO P0: from `python -m py_vapid --gen`
};

const $ = (id) => document.getElementById(id);
const status = (msg, cls = "") => { $("status").textContent = msg; $("status").className = cls; };
const getToken = () => localStorage.getItem("forge_token") || "";

function urlB64ToUint8Array(b64) {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

async function api(path, opts = {}) {
  const res = await fetch(CONFIG.API_BASE + path, {
    ...opts,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}`, ...(opts.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.status === 204 ? null : res.json();
}

$("saveToken").onclick = () => {
  localStorage.setItem("forge_token", $("token").value.trim());
  status("Token saved on device.", "ok");
};

$("enablePush").onclick = async () => {
  try {
    if (!("serviceWorker" in navigator)) return status("No service worker support.", "warn");
    const reg = await navigator.serviceWorker.register("sw.js");
    const perm = await Notification.requestPermission();
    if (perm !== "granted") return status("Permission denied. iOS: app must be installed via Safari → Add to Home Screen.", "warn");
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlB64ToUint8Array(CONFIG.VAPID_PUBLIC_KEY),
    });
    const j = sub.toJSON();
    await api("/v1/push/subscriptions", {
      method: "POST",
      body: JSON.stringify({ endpoint: j.endpoint, p256dh: j.keys.p256dh, auth: j.keys.auth, ua: navigator.userAgent }),
    });
    status("Subscribed ✓ — send a test push from Rig 2.\n" + JSON.stringify(j, null, 2), "ok");
  } catch (e) { status("Failed: " + e.message, "warn"); }
};

if (getToken()) $("token").placeholder = "token saved — paste to replace";
// TODO P3: IndexedDB offline queue, composer POST /v1/logs, today feed, reports + jsPDF export.
