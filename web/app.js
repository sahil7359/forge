// Forge PWA — vanilla JS, no build step (Rules R4). Flows per docs/AppFlow.md.
"use strict";

const CONFIG = {
  API_BASE: "https://forge-tuvr.onrender.com",
  VAPID_PUBLIC_KEY:
    "BA8ke0txn2aswP8vVBE5y8YqcepoMx9TcNfGOVOBsenuzmhnxEEdhH2UQNVKuAed-d-330RIa_l0PO8KUGlKDdw",
  SLOW_MS: 3000, // Render cold start -> "waking server…" banner
};

const $ = (id) => document.getElementById(id);
const getToken = () => localStorage.getItem("forge_token") || "";
const IST = { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hour12: false };
const fmtTime = (iso) => new Date(iso).toLocaleTimeString("en-IN", IST);

// ---------------------------------------------------------------- banner
let bannerTimer = null;
function banner(msg, sticky = false) {
  const el = $("banner");
  if (!msg) { el.classList.remove("show"); return; }
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(bannerTimer);
  if (!sticky) bannerTimer = setTimeout(() => el.classList.remove("show"), 4000);
}

// ---------------------------------------------------------------- API client
async function api(path, opts = {}) {
  const slow = setTimeout(() => banner("waking server…", true), CONFIG.SLOW_MS);
  try {
    const res = await fetch(CONFIG.API_BASE + "/v1" + path, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getToken()}`,
        ...(opts.headers || {}),
      },
    });
    if (res.status === 401) { banner("Token rejected — check Settings."); throw new Error("401"); }
    if (!res.ok) throw new Error(`${res.status}`);
    return res.status === 204 ? null : await res.json();
  } finally {
    clearTimeout(slow);
    if ($("banner").textContent === "waking server…") banner(null);
  }
}

// ---------------------------------------------------------------- offline queue (IndexedDB)
let db;
function idb() {
  if (db) return Promise.resolve(db);
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("forge", 1);
    req.onupgradeneeded = () => req.result.createObjectStore("queue", { autoIncrement: true });
    req.onsuccess = () => {
      const d = req.result;
      if (!d.objectStoreNames.contains("queue")) {
        // self-heal a partially created db — the queue store is the only data here
        d.close();
        const del = indexedDB.deleteDatabase("forge");
        del.onsuccess = del.onerror = () => idb().then(resolve, reject);
        return;
      }
      db = d;
      resolve(db);
    };
    req.onerror = () => reject(req.error);
  });
}
function idbOp(mode, fn) {
  return idb().then(
    (d) =>
      new Promise((resolve, reject) => {
        const tx = d.transaction("queue", mode);
        const out = fn(tx.objectStore("queue"));
        tx.oncomplete = () => resolve(out.result !== undefined ? out.result : out);
        tx.onerror = () => reject(tx.error);
      })
  );
}
const qAdd = (entry) => idbOp("readwrite", (s) => s.add(entry));
const qAll = () =>
  idbOp("readonly", (s) => {
    const req = s.getAll();
    const keys = s.getAllKeys();
    return { get result() { return { items: req.result, keys: keys.result }; } };
  });
const qDel = (key) => idbOp("readwrite", (s) => s.delete(key));

async function queueCount() {
  const { items } = await qAll();
  return items.length;
}
async function updateQueueBanner() {
  const n = await queueCount();
  if (n > 0) banner(`offline — ${n} item${n > 1 ? "s" : ""} queued`, true);
  else if ($("banner").textContent.startsWith("offline")) banner(null);
}

let syncing = false;
async function syncQueue() {
  if (syncing || !navigator.onLine || !getToken()) return;
  syncing = true;
  try {
    const { items, keys } = await qAll();
    for (let i = 0; i < items.length; i++) {
      const e = items[i];
      try {
        await api(e.path, { method: "POST", body: JSON.stringify(e.payload) });
        await qDel(keys[i]);
      } catch (err) {
        if (String(err.message) === "401") break; // token problem — keep queue intact
        break; // network/server — retry on next trigger
      }
    }
  } finally {
    syncing = false;
    updateQueueBanner();
    refreshToday();
  }
}

// ---------------------------------------------------------------- composer
let chipType = "checkin";
let dwMinutes = 60;

$("chips").addEventListener("click", (e) => {
  const btn = e.target.closest(".chip");
  if (!btn) return;
  chipType = btn.dataset.type;
  document.querySelectorAll("#chips .chip").forEach((c) => c.classList.toggle("on", c === btn));
  $("amountField").classList.toggle("show", chipType === "expense");
  $("minutesField").classList.toggle("show", chipType === "deepwork");
});
$("minutesStepper").addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  dwMinutes = Number(btn.dataset.min);
  document.querySelectorAll("#minutesStepper button").forEach((b) => b.classList.toggle("on", b === btn));
});
$("composer").addEventListener("input", function () {
  this.style.height = "auto";
  this.style.height = this.scrollHeight + "px";
});

$("logBtn").onclick = async () => {
  const text = $("composer").value.trim();
  if (!text) return;
  const data = {};
  let type = chipType;
  if (chipType === "expense") {
    const amt = parseFloat($("amount").value);
    if (!Number.isNaN(amt)) data.amount = amt;
  } else if (chipType === "deepwork") {
    type = "checkin";
    data.block_minutes = dwMinutes;
  }
  const log = { id: crypto.randomUUID(), type, text, data, ts: new Date().toISOString() };
  const jobs = [{ path: "/logs", payload: log }];
  if (chipType === "task")
    jobs.push({ path: "/tasks", payload: { title: text.slice(0, 300), origin_log_id: log.id } });

  // optimistic insert (Design §7)
  prependFeedRow({ ts: log.ts, type, text, data }, true);
  $("composer").value = "";
  $("composer").style.height = "auto";
  $("amount").value = "";

  for (const job of jobs) {
    try {
      if (!navigator.onLine) throw new Error("offline");
      await api(job.path, { method: "POST", body: JSON.stringify(job.payload) });
    } catch (err) {
      if (String(err.message) !== "401") await qAdd(job);
    }
  }
  await updateQueueBanner();
  refreshToday();
};

// ---------------------------------------------------------------- today feed
function feedRow(log, pending = false) {
  const row = document.createElement("div");
  row.className = "row" + (pending ? " pending-retry" : "");
  const time = document.createElement("span");
  time.className = "time";
  time.textContent = fmtTime(log.ts);
  const body = document.createElement("span");
  body.className = "body";
  body.textContent = log.text; // textContent only — user text is untrusted (Security §6)
  if (log.type !== "checkin") {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = log.type;
    body.appendChild(tag);
  }
  if ((log.data || {}).block_minutes) {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = `[deep work ${log.data.block_minutes}m]`;
    body.appendChild(tag);
  }
  row.append(time, body);
  return row;
}
function prependFeedRow(log, pending) {
  const feed = $("feed");
  if (feed.firstElementChild?.tagName === "P") feed.textContent = "";
  feed.prepend(feedRow(log, pending));
}

async function refreshToday() {
  if (!getToken()) return;
  try {
    const t = await api("/today");
    $("dayCounter").textContent = t.day_counter ? `Day ${t.day_counter}/${t.day_total}` : "Forge";
    $("streak").textContent = t.streak ? `🔥 ${t.streak}` : "";
    $("pendingCount").textContent = t.pending_tasks.length ? `${t.pending_tasks.length} pending` : "";
    $("expenses").textContent = t.stats.expenses_today ? `₹${t.stats.expenses_today}` : "";
    const feed = $("feed");
    feed.textContent = "";
    if (!t.logs.length) {
      const p = document.createElement("p");
      p.className = "meta";
      p.textContent = "Nothing logged yet. The 07:00 coach reads yesterday's plan.";
      feed.appendChild(p);
    } else {
      [...t.logs].reverse().forEach((l) => feed.appendChild(feedRow(l)));
    }
    const { items } = await qAll(); // queued offline logs stay visible with a retry mark
    items
      .filter((e) => e.path === "/logs")
      .reverse()
      .forEach((e) => {
        if (feed.firstElementChild?.tagName === "P") feed.textContent = "";
        feed.prepend(feedRow(e.payload, true));
      });
    renderTasks(t.pending_tasks);
  } catch (_) {
    /* offline / cold start — feed keeps last render */
  }
}

function renderTasks(tasks) {
  $("tasksCard").hidden = !tasks.length;
  const list = $("taskList");
  list.textContent = "";
  tasks.forEach((t) => {
    const row = document.createElement("div");
    row.className = "row task-row";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.ariaLabel = `close task ${t.title}`;
    cb.onchange = async () => {
      if (!navigator.onLine) { cb.checked = false; banner("Task close needs a connection."); return; }
      row.classList.add("done");
      try { await api(`/tasks/${t.id}`, { method: "PATCH", body: JSON.stringify({ status: "done" }) }); }
      catch (_) { row.classList.remove("done"); cb.checked = false; }
      refreshToday();
    };
    const body = document.createElement("span");
    body.className = "body";
    body.textContent = t.title;
    const age = document.createElement("span");
    age.className = "tag" + (t.age_hours > 24 ? " warn" : "");
    age.textContent = `${t.age_hours}h`;
    body.appendChild(age);
    row.append(cb, body);
    list.appendChild(row);
  });
}

// ---------------------------------------------------------------- reports
let currentArchive = null;

function listItem(title, sub, onClick) {
  const el = document.createElement("div");
  el.className = "list-item";
  const strong = document.createElement("div");
  strong.textContent = title;
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = sub;
  el.append(strong, meta);
  el.onclick = onClick;
  return el;
}

function renderMd(md) {
  $("reportMd").innerHTML = DOMPurify.sanitize(marked.parse(md)); // LLM output — always sanitized
}

function showReportView(meta, md, archive = null) {
  currentArchive = archive;
  $("reportLists").style.display = "none";
  $("reportView").style.display = "block";
  $("reportMeta").textContent = meta;
  $("pdfBtn").hidden = !archive;
  renderMd(md);
}
$("backBtn").onclick = () => {
  $("reportView").style.display = "none";
  $("reportLists").style.display = "block";
};

async function refreshReports() {
  if (!getToken()) return;
  try {
    const [{ reports }, { archives }] = await Promise.all([api("/reports"), api("/archives")]);
    const daily = $("dailyList");
    daily.textContent = "";
    if (!reports.length) {
      daily.innerHTML = "";
      const p = document.createElement("p");
      p.className = "meta";
      p.textContent = "First report lands tonight at 00:05.";
      daily.appendChild(p);
    }
    reports.forEach((r) =>
      daily.appendChild(
        listItem(
          r.date + (r.kind === "daily_fallback" ? " · stats-only (Rig 2 was off)" : ""),
          (r.preview || "").split("\n")[0].slice(0, 80),
          async () => {
            const full = await api(`/reports/${r.date}`);
            showReportView(`Daily report · ${full.date} · ${full.kind}`, full.md);
          }
        )
      )
    );
    const arch = $("archiveList");
    arch.textContent = "";
    if (!archives.length) {
      const p = document.createElement("p");
      p.className = "meta";
      p.textContent = "First archive lands on the 1st, 00:25.";
      arch.appendChild(p);
    }
    const years = new Set();
    archives.forEach((a) => {
      years.add(a.ym.slice(0, 4));
      const c = a.counts || {};
      arch.appendChild(
        listItem(a.ym, `${c.logs ?? "?"} logs · ${c.nudges ?? "?"} nudges · ${c.reports ?? "?"} reports`, async () => {
          const full = await api(`/archives/${a.ym}`);
          showReportView(`Monthly archive · ${full.ym}`, full.md, full);
        })
      );
    });
    const pick = $("yearPick");
    pick.textContent = "";
    [...years].sort().reverse().forEach((y) => {
      const o = document.createElement("option");
      o.value = o.textContent = y;
      pick.appendChild(o);
    });
    $("yearPdf").disabled = years.size === 0;
  } catch (_) {
    /* offline — keep last render */
  }
}

// ---------------------------------------------------------------- PDF export (jsPDF)
function pdfDoc() {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  doc.setFont("courier", "normal");
  doc.setFontSize(9);
  return doc;
}
function pdfWrite(doc, lines, state) {
  for (const line of lines) {
    if (state.y > 282) { doc.addPage(); state.y = 12; }
    doc.text(line, 12, state.y);
    state.y += 4.2;
  }
}
function archiveLines(archive) {
  const out = [];
  out.push(`FORGE MONTHLY ARCHIVE ${archive.ym}`, "");
  out.push(...archive.md.split("\n"));
  out.push("", "=".repeat(80), `APPENDIX — full timestamped record (${archive.ym})`, "=".repeat(80));
  const raw = archive.raw || {};
  for (const section of ["logs", "nudges", "reports"]) {
    out.push("", `--- ${section} (${(raw[section] || []).length}) ---`);
    for (const item of raw[section] || []) {
      const ts = item.ts || item.date || "";
      const text = item.text || item.title || item.kind || "";
      out.push(`${ts}  ${item.type || item.kind || ""}  ${text}`.slice(0, 110));
    }
  }
  return out;
}
function wrap(doc, lines) {
  return lines.flatMap((l) => doc.splitTextToSize(l || " ", 186));
}
$("pdfBtn").onclick = () => {
  if (!currentArchive) return;
  const doc = pdfDoc();
  pdfWrite(doc, wrap(doc, archiveLines(currentArchive)), { y: 12 });
  doc.save(`forge-${currentArchive.ym}.pdf`);
};
$("yearPdf").onclick = async () => {
  const year = $("yearPick").value;
  if (!year) return;
  $("yearStatus").textContent = "compiling…";
  try {
    const { archives } = await api("/archives");
    const months = archives.filter((a) => a.ym.startsWith(year)).sort((a, b) => a.ym.localeCompare(b.ym));
    const doc = pdfDoc();
    const state = { y: 12 };
    pdfWrite(doc, wrap(doc, [`FORGE YEARLY COMPILATION ${year}`, `${months.length} month(s)`, ""]), state);
    for (const m of months) {
      const full = await api(`/archives/${m.ym}`);
      pdfWrite(doc, wrap(doc, ["", "#".repeat(80), ...archiveLines(full)]), state);
    }
    doc.save(`forge-${year}.pdf`);
    $("yearStatus").textContent = `saved forge-${year}.pdf`;
  } catch (_) {
    $("yearStatus").textContent = "failed — check connection";
  }
};

// ---------------------------------------------------------------- settings
$("saveToken").onclick = () => {
  localStorage.setItem("forge_token", $("token").value.trim());
  $("token").value = "";
  $("token").placeholder = "token saved — paste to replace";
  banner("Token saved on device.");
  boot();
};

async function loadSettings() {
  if (!getToken()) return;
  try {
    const s = await api("/settings");
    $("setStart").value = s.active_start;
    $("setEnd").value = s.active_end;
    $("setGap").value = s.nudge_min_gap_min;
    $("setHard").value = s.hard_mode_after_hours;
  } catch (_) { /* offline */ }
}
$("saveSettings").onclick = async () => {
  const body = {
    active_start: Number($("setStart").value),
    active_end: Number($("setEnd").value),
    nudge_min_gap_min: Number($("setGap").value),
    hard_mode_after_hours: Number($("setHard").value),
  };
  try {
    await api("/settings", { method: "PATCH", body: JSON.stringify(body) });
    $("settingsStatus").textContent = "Saved ✓ (agent picks it up next hour)";
    $("settingsStatus").className = "ok";
  } catch (_) {
    $("settingsStatus").textContent = "Save failed — check token/connection.";
    $("settingsStatus").className = "warn";
  }
};

// ---------------------------------------------------------------- push
function urlB64ToUint8Array(b64) {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}
$("enablePush").onclick = async () => {
  const out = $("pushStatus");
  try {
    if (!("serviceWorker" in navigator)) { out.textContent = "No service worker support."; return; }
    const reg = await navigator.serviceWorker.ready;
    const perm = await Notification.requestPermission();
    if (perm !== "granted") {
      out.textContent = "Permission denied. iOS: install via Safari → Add to Home Screen, open from the icon.";
      return;
    }
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlB64ToUint8Array(CONFIG.VAPID_PUBLIC_KEY),
    });
    const j = sub.toJSON();
    out.textContent = "Subscribed ✓\n" + JSON.stringify(j, null, 2);
    out.className = "ok";
    try {
      await api("/push/subscriptions", {
        method: "POST",
        body: JSON.stringify({ endpoint: j.endpoint, p256dh: j.keys.p256dh, auth: j.keys.auth, ua: navigator.userAgent }),
      });
      out.textContent = "Subscribed ✓ — stored on server. Nudges will arrive on the hour.";
    } catch (_) {
      out.textContent += "\n(server store failed — will retry on next launch)";
    }
  } catch (e) {
    out.textContent = "Failed: " + e.message;
    out.className = "warn";
  }
};

// ---------------------------------------------------------------- tabs + health + boot
document.querySelector("nav").addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  document.querySelectorAll("nav button").forEach((b) => b.classList.toggle("on", b === btn));
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("on"));
  $(`tab-${btn.dataset.tab}`).classList.add("on");
  if (btn.dataset.tab === "reports") refreshReports();
  if (btn.dataset.tab === "settings") loadSettings();
});

async function health() {
  const dot = $("healthDot");
  const started = performance.now();
  dot.className = "dot waking";
  $("healthText").textContent = "API: waking…";
  try {
    const res = await fetch(CONFIG.API_BASE + "/healthz");
    const ms = Math.round(performance.now() - started);
    dot.className = res.ok ? "dot up" : "dot";
    $("healthText").textContent = res.ok ? `API: up (${ms} ms)` : `API: ${res.status}`;
  } catch (_) {
    dot.className = "dot";
    $("healthText").textContent = "API: unreachable";
  }
}

window.addEventListener("online", () => { banner(null); syncQueue(); });
window.addEventListener("offline", updateQueueBanner);

async function boot() {
  if ("serviceWorker" in navigator) {
    try {
      await navigator.serviceWorker.register("sw.js");
      $("swState").textContent = "offline-ready";
    } catch (_) { $("swState").textContent = "sw failed"; }
  }
  if (getToken()) $("token").placeholder = "token saved — paste to replace";
  health();
  await syncQueue();
  refreshToday();
}
boot();
