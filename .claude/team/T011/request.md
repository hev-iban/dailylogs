# T011 request: theme switch in the header (upper right)

Project root: C:/Users/Ivan/Desktop/A-Finals. Windows host, Git Bash, Python at .venv/Scripts/python.exe, Node 22,
Chrome at "C:/Program Files/Google/Chrome/Application/chrome.exe" (headless + CDP: real clicks/keyboard, screenshots,
Emulation.setEmulatedMedia for prefers-color-scheme / prefers-reduced-motion, Emulation.setDeviceMetricsOverride for phone width).
The user builds in explicit stages. Implement ONLY this stage.

## Current state (user-verified, must keep working)
- frontend/style.css (530 lines): X-inspired. Colors are CSS custom properties on :root (line ~3); dark overrides are in
  `@media (prefers-color-scheme: dark) { :root { ... } }` (line ~27). Sticky `header` (line ~79) holds h1 "DailyLog".
  All T008 interaction states (hover only under (hover:hover) and (pointer:fine), 3px :focus-visible ring, :active shrink,
  aria-busy loading indicator, error areas, contrast >= 4.5:1 text in both themes, reduced-motion support) and the T010
  char counter / over-limit message styles.
- frontend/index.html: header > h1 "DailyLog"; loads /static/style.css and /static/app.js (script at end of body).
- frontend/app.js: load/render posts, create, edit, delete, error wording, T010 description limit. Do not change that behavior.
- backend: 130 passing tests. UNCHANGED in this task.

## What the user asked (binding)
"add a switch theme on the header upper right" (everything else in the styling is approved).

## Orchestrator defaults (the user did not specify these; keep them simple)
- One button at the right end of the sticky header, on the same row as "DailyLog", including at 360px width.
- Two states: light and dark. On first visit (no saved choice) the page follows the system prefers-color-scheme, exactly as today.
  Clicking switches to the other theme and remembers the choice in localStorage (key e.g. "dailylog-theme"); the saved choice
  wins over the system setting on later visits. If localStorage is unavailable (throws), the switch still works for the session.
- Apply the theme via an attribute on <html> (e.g. data-theme="light"|"dark") so the explicit choice overrides the media query in
  both directions (light chosen while the system is dark, and dark chosen while the system is light). Avoid duplicating the dark
  token list if a clean way exists; correctness first.
- No flash of the wrong theme on reload: the saved theme must be applied before first paint (a tiny inline script in <head>
  is acceptable; record why).
- Accessible: a real <button>, keyboard reachable (Tab order: header switch first, then the form), clear accessible name that
  says what it does (e.g. aria-label "Switch to dark theme" updated after each toggle, or aria-pressed with a fixed label),
  a visible icon/text (e.g. a moon / sun glyph, no external icon libraries), target >= 24x24 CSS px, same T008 states
  (rest looks like a control, hover only on fine pointers, :focus-visible ring, :active feedback), contrast >= 3:1 for the
  icon and >= 4.5:1 for any text, in both themes.
- No external fonts, libraries or CDNs. No new files.

## Constraints
- Edit only frontend/index.html, frontend/style.css, frontend/app.js.
- Every existing color/contrast result from T008 and T010 must still hold in both themes, whichever way the theme was chosen.
- Backend untouched; all 130 tests still pass.
- NEVER touch the project's real logs.db or uploads/ (the user's real posts). The user's own server may be running on port 8000:
  never use port 8000; pick a free high port, check it with netstat first, start create_app(temp_db, temp_uploads) from a script
  outside the project, and confirm GET /api/logs returns [] before any write. Kill only processes you started
  (match the temp Chrome profile path / your server PID), never all chrome.exe.
- OUT OF SCOPE: a third "system" option, other style changes, docs, Docker.
