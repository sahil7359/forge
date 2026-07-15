# Design — Forge v1

Mobile-first, dark-only, one-hand usable. The app must make logging faster than ignoring the
nudge. Aesthetic: forge/ember — dark steel + one hot accent, zero decoration.

## 1. Tokens

```css
:root {
  --bg:        #0B0E14;   /* page */
  --surface:   #151A23;   /* cards, composer */
  --surface-2: #1C2330;   /* pressed / nested */
  --border:    #232B38;
  --text:      #E6EAF2;
  --text-dim:  #8B94A7;
  --ember:     #F97316;   /* accent: streaks, primary button, active tab */
  --ok:        #2DD4A7;   /* done tasks, success */
  --warn:      #F5B841;   /* pending > 24 h, fallback banners */
  --danger:    #EF4444;   /* hard-mode chip, destructive */
  --radius: 14px; --radius-sm: 10px;
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
}
```
Type scale: 26/600 (day header) · 20/600 (section) · 16/400 (body, min for iOS no-zoom inputs) ·
13/400 (meta, --text-dim). Spacing: 4-pt grid (8/12/16/24). Contrast ≥ 4.5:1 everywhere
(all pairs above pass on their surfaces).

## 2. Layout

Single column, max-width 480 px centered. Bottom tab bar, 3 tabs: **Today · Reports · Settings**
(ti-style outline icons + label, active = --ember). Safe areas: `padding: env(safe-area-inset-*)`;
heights via `100dvh`; tab bar fixed with safe-area-bottom padding.

## 3. Today (home)

1. **Header strip:** `Day 12/84` · streak `🔥 9` (ember, count only — no emoji elsewhere) ·
   pending tasks count chip · expenses today. Single line, 13 px meta row under date.
2. **Composer (the hero):** auto-growing textarea, placeholder "What moved?"; chip row beneath:
   `check-in (default) · task · expense · fitness · habit · deep work`. Selecting `expense`
   reveals inline amount field (numeric, ₹); `deep work` reveals minutes stepper (30/60/90/120).
   Primary button **Log** (ember, full-width, 48 px). Enter = newline; Log sends.
3. **Today feed:** reverse-chronological cards — time (13 px dim) + text + type chip; task-type
   rows show a checkbox to close (`done` strikes through, --ok). Nudges appear inline as slim
   dim rows ("14:00 · coach: …") so conversation context is visible. Deep-work blocks render as
   a bracketed span row.
4. **Offline banner:** thin --warn strip "offline — 2 logs queued" when queue non-empty.

## 4. Reports

List grouped: **Daily** (current + previous month, newest first: date + first line preview) ·
**Monthly archives** (forever: `2026-07 · 412 logs · ₹8,340`) · **Yearly** (year picker).
Report view: sanitized rendered markdown (DOMPurify), section headers styled 20/600; sticky
footer button **Download PDF**. Monthly/yearly PDFs include the full timestamped appendix.
Fallback reports show a --warn chip "stats-only (Rig 2 was off)".

## 5. Settings

Token entry (masked, saved on device) · Enable notifications + **Test push** · active window
(start/end steppers) · nudge min gap · hard-mode threshold · privacy toggle "generic
notification titles" · install help ("open in Safari → Share → Add to Home Screen") · version +
API health dot.

## 6. Notifications (content design)

Title ≤ 40 chars = status snapshot ("Day 12 · chunker open" / "2h quiet" / "4h dark").
Body ≤ 220 chars, plain text, ends with one concrete ask. No emoji. Hard-mode (L3) titles are
blunt but factual. `report_ready`: "Day 12 report ready — 6.5 h logged, plan for tomorrow inside."
Privacy toggle swaps titles for "Forge" and bodies for "Check in." (Security §6).

## 7. States & feel

- Optimistic log insert (< 100 ms perceived); failed sync = row gets retry icon.
- Cold-start state: skeleton feed + "waking server…" caption (Render free tier honesty).
- Empty states: Today — "Nothing logged yet. The 07:00 coach read yesterday's plan."; Reports —
  "First report lands tonight at 00:05."
- Haptic-adjacent: button active states darken to --surface-2; no animations > 150 ms.
- PWA: `display: standalone`, `theme-color #0B0E14`, apple-touch-icon 180 px, maskable 192/512.
  App icon: ember square-anvil glyph on #0B0E14 (supplied in /web/icons).

## 8. Accessibility

Focus-visible rings (--ember, 2 px); all touch targets ≥ 44 px; feed is a list with time
labels readable by VoiceOver; report markdown uses real heading elements; color never sole
carrier (task state = checkbox + strikethrough).
