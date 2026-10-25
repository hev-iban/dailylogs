# T008 request: style the page (style.css), X-inspired, with full interaction states

Project root: C:/Users/Ivan/Desktop/A-Finals. Windows host, Git Bash, Python at .venv/Scripts/python.exe, Node 22.
Chrome at "C:/Program Files/Google/Chrome/Application/chrome.exe" (headless + CDP for real clicks, keyboard, screenshots,
Emulation.setEmulatedMedia for prefers-color-scheme / prefers-reduced-motion, Emulation.setDeviceMetricsOverride for phone width).
The user builds in explicit stages. Implement ONLY this stage.

## Current state (passed verification, must keep working)
- frontend/index.html: header h1 "DailyLog"; section#new-log > form#log-form (label+textarea#description, label+input#photos
  type=file multiple accept=.jpg,.jpeg,.png,.webp, p#form-error[role=alert][hidden], button#save-button "Save");
  section#logs > h2, ul#log-list, p#empty-message[hidden]; template#log-template li.log > time.log-date, p.log-description,
  div.log-photos, div.log-actions > button.edit-button, button.delete-button.
- frontend/app.js: creates p#load-error[role=alert] before #log-list; renders posts; create form Save (disables #save-button during request);
  inline edit form per post: form.edit-form > textarea, label.edit-photo (img + checkbox + " Remove") per photo, file input,
  p.edit-error[role=alert], button.edit-save-button, button.edit-cancel-button; one post in edit mode at a time; Delete with
  window.confirm, disables the delete button during request, shows errors in the post. Error text = API "detail" string
  (e.g. "invalid or corrupt image", "photo exceeds 5 MiB", "a log needs between 1 and 5 photos", "log not found")
  or fallback messages.
- frontend/style.css: EMPTY.
- backend: 112 passing tests; serves /, /static/, /uploads/, /api/logs (GET, POST), /api/logs/{id} (PUT, DELETE).
Read frontend/index.html and frontend/app.js for exact class names before styling.

## What the user asked (binding)
"now style the page with style.css" + this brief (verbatim):
  Easterned UX inspired by X.  [orchestrator reading: an X (Twitter)-inspired look]
  Default / Resting Appearance: Define the normal appearance of interface components.
  Hover: Apply to pointer devices only. Must not be the sole affordance.
  Focus Visible: Provide a visible focus indicator. Ensure keyboard reachability. Follow WCAG 2.2 minimum requirements.
  Active / Pressed: Provide immediate acknowledgment of user input.
  Selected: Show when the component participates in selection.
  Disabled: Explain the reason, or hide the control instead.
  Loading: Distinguish loading from disabled. Clearly convey that work is in progress.
  Error: State what failed and what to do next.

## Design direction (orchestrator defaults)
- X-inspired: centered single column feed (~600px max), sticky header, posts separated by thin dividers, rounded-full pill
  buttons, X blue primary (#1d9bf0-ish) for Save, neutral outline for Edit/Cancel, red for Delete, system font stack,
  photo grid inside posts with rounded corners, muted secondary text for the date.
- Light and dark themes via prefers-color-scheme, colors as CSS custom properties on :root.
- Responsive down to 360px wide with no horizontal scroll.
- No external fonts, libraries or CDNs.

## State requirements -> concrete acceptance
- Hover: only inside @media (hover: hover) and (pointer: fine); every hover-styled control must also be distinguishable at rest
  (e.g. buttons look like buttons without hover).
- Focus visible: :focus-visible outline on every interactive element (buttons, textareas, file inputs, checkboxes) with
  >= 3:1 contrast against adjacent colors and not obscured (WCAG 2.2 SC 2.4.7, 2.4.11, 1.4.11). All controls reachable by Tab
  in a logical order. Interactive targets >= 24x24 CSS px (SC 2.5.8).
- Text contrast >= 4.5:1 (normal text) in both themes, including the muted date and error text (SC 1.4.3).
- Active/pressed: visible :active feedback (e.g. darker/shrunk) with no delay.
- Selected: a photo whose "Remove" checkbox is checked in the edit form is visibly marked (e.g. dimmed + red outline + label
  text state), not by color alone.
- Disabled vs loading: the only disabled moments today are in-flight requests, which are LOADING. app.js must mark in-flight
  buttons with aria-busy="true" and an in-progress label (e.g. "Saving..." / "Deleting...") and CSS shows a spinner/progress
  indicator for [aria-busy="true"]; restore the original label afterwards. Respect prefers-reduced-motion (no spinning animation;
  still a clear static indicator). No control should be disabled without a visible reason.
- Error: error areas styled clearly (icon or prefix not relying on color alone). app.js should present each error as
  what failed + what to do next, e.g. "Couldn't save your log: invalid or corrupt image. Choose a JPG, PNG or WEBP photo and try
  again." Map known API detail strings to a next-step hint, with a generic "Please try again." fallback. Keep the API detail text
  visible. Same for edit, delete and load errors. Errors clear on the next attempt (existing behavior).

## Constraints
- Edit only frontend/style.css and frontend/app.js. index.html only if strictly necessary (record why). No new files.
- app.js changes limited to: aria-busy/labels for loading, error-message wording/hints. Do not change request logic, ordering,
  one-edit-at-a-time behavior, or use innerHTML with user/API data.
- Backend untouched; all 112 tests still pass.
- NEVER touch the project's real logs.db or uploads/ (user's real posts). Use temp paths for any live run.
- OUT OF SCOPE: an "edited" indicator, new features, docs, Docker.
