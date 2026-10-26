"use strict";

const logList = document.getElementById("log-list");
const emptyMessage = document.getElementById("empty-message");
const logTemplate = document.getElementById("log-template");
const loadError = document.createElement("p");
loadError.id = "load-error";
loadError.setAttribute("role", "alert");
loadError.hidden = true;
logList.before(loadError);

// Theme switch: the head script in index.html applies a saved choice before first paint.
const THEME_KEY = "dailylog-theme";
const themeToggle = document.getElementById("theme-toggle");
const themeIcon = document.getElementById("theme-icon");

function currentTheme() {
  const set = document.documentElement.getAttribute("data-theme");
  if (set === "light" || set === "dark") {
    return set;
  }
  const dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  return dark ? "dark" : "light";
}

function syncThemeToggle() {
  // Glyph and name show the theme a click switches to.
  const target = currentTheme() === "dark" ? "light" : "dark";
  themeToggle.setAttribute("aria-label", "Switch to " + target + " theme");
  themeIcon.textContent = target === "dark" ? "☾︎" : "☀︎";
}

themeToggle.addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch (error) {
    // Storage unavailable: the choice lasts for this session only.
  }
  syncThemeToggle();
});

if (window.matchMedia) {
  // With no explicit choice the page follows the system setting, so keep the label in step.
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", syncThemeToggle);
}
syncThemeToggle();

function formatDate(iso) {
  // created_at is UTC; treat a timestamp without an offset as UTC.
  const hasZone = /(Z|[+-]\d{2}(:?\d{2})?)$/i.test(iso);
  const date = new Date(hasZone ? iso : iso + "Z");
  if (Number.isNaN(date.getTime())) {
    return String(iso);
  }
  return date.toLocaleString();
}

function photoUrl(path) {
  // API gives "uploads/<file>"; make it a same-origin absolute URL.
  const name = String(path).replace(/^\/+/, "").replace(/^uploads\//, "");
  return "/uploads/" + name.split("/").map(encodeURIComponent).join("/");
}

function renderLog(log) {
  const item = logTemplate.content.firstElementChild.cloneNode(true);
  const time = item.querySelector(".log-date");
  time.setAttribute("datetime", log.created_at);
  time.textContent = formatDate(log.created_at);
  item.querySelector(".log-description").textContent = log.description;
  const photos = item.querySelector(".log-photos");
  for (const path of log.photos) {
    const img = document.createElement("img");
    img.src = photoUrl(path);
    img.alt = "Log photo";
    photos.appendChild(img);
  }
  item.querySelector(".edit-button").addEventListener("click", () => startEdit(item, log));
  const deleteButton = item.querySelector(".delete-button");
  deleteButton.addEventListener("click", () => deleteLog(item, log, deleteButton));
  return item;
}

async function deleteLog(item, log, button) {
  if (button.disabled || !window.confirm("Delete this post and its photos?")) {
    return;
  }
  let error = item.querySelector(".delete-error");
  if (!error) {
    error = document.createElement("p");
    error.className = "delete-error";
    error.setAttribute("role", "alert");
    error.hidden = true;
    item.appendChild(error);
  }
  error.hidden = true;
  error.textContent = "";
  setBusy(button, "Deleting...");
  try {
    const response = await fetch("/api/logs/" + encodeURIComponent(log.id), {
      method: "DELETE",
    });
    if (!response.ok) {
      error.textContent = await errorMessage(response, "Couldn't delete your log");
      error.hidden = false;
      return;
    }
    // The reload resets any edit state (renderLogs), so no stale form remains.
    await loadLogs();
  } catch (err) {
    error.textContent = networkMessage("Couldn't delete your log");
    error.hidden = false;
  } finally {
    clearBusy(button, "Delete");
  }
}

const MAX_DESCRIPTION = 200;

// Code points of the trimmed text, matching the server's len(description.strip()).
function descriptionLength(value) {
  return [...value.trim()].length;
}

// Wires a live "N/200" counter and an over-limit message to a textarea and its
// Save button. Returns refresh(), which must also be called after any
// programmatic change (form.reset() fires no input event).
function attachLimit(textarea, counter, message, save) {
  function refresh() {
    const count = descriptionLength(textarea.value);
    const over = count > MAX_DESCRIPTION;
    counter.textContent = count + "/" + MAX_DESCRIPTION;
    counter.classList.toggle("over-limit", over);
    if (over) {
      const extra = count - MAX_DESCRIPTION;
      message.textContent = "Description is too long: " + count + "/" + MAX_DESCRIPTION +
        " characters. Remove " + extra + (extra === 1 ? " character" : " characters") + " to post.";
      textarea.setAttribute("aria-invalid", "true");
    } else {
      message.textContent = "";
      textarea.removeAttribute("aria-invalid");
    }
    message.hidden = !over;
    // An in-flight save keeps the button disabled (loading wins over over-limit).
    save.disabled = over || save.getAttribute("aria-busy") === "true";
    return over;
  }
  textarea.setAttribute("aria-describedby", counter.id + " " + message.id);
  textarea.addEventListener("input", refresh);
  refresh();
  return refresh;
}

// Only one post is in edit mode at a time; starting another edit cancels the first.
let editing = null;

function cancelEdit() {
  if (editing) {
    editing.form.remove();
    for (const el of editing.hidden) {
      el.hidden = false;
    }
    editing = null;
  }
}

function startEdit(item, log) {
  cancelEdit();
  const form = document.createElement("form");
  form.className = "edit-form";

  const textarea = document.createElement("textarea");
  textarea.name = "description";
  textarea.rows = 4;
  textarea.value = log.description;
  textarea.setAttribute("aria-label", "Description");
  form.appendChild(textarea);

  const counter = document.createElement("p");
  counter.id = "edit-description-count";
  counter.className = "char-count";
  const status = document.createElement("div");
  status.className = "limit-status";
  status.setAttribute("aria-live", "polite");
  const limitMessage = document.createElement("p");
  limitMessage.id = "edit-description-limit";
  limitMessage.className = "limit-message";
  limitMessage.hidden = true;
  status.appendChild(limitMessage);
  form.append(counter, status);

  const checks = [];
  for (const path of log.photos) {
    const label = document.createElement("label");
    label.className = "edit-photo";
    const img = document.createElement("img");
    img.src = photoUrl(path);
    img.alt = "Log photo";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.value = path;
    checks.push(box);
    label.append(img, box, " Remove");
    form.appendChild(label);
  }

  const files = document.createElement("input");
  files.type = "file";
  files.name = "photos";
  files.accept = ".jpg,.jpeg,.png,.webp";
  files.multiple = true;
  files.setAttribute("aria-label", "Add photos");
  form.appendChild(files);

  const error = document.createElement("p");
  error.className = "edit-error";
  error.setAttribute("role", "alert");
  error.hidden = true;
  form.appendChild(error);

  const save = document.createElement("button");
  save.type = "submit";
  save.className = "edit-save-button";
  save.textContent = "Save";
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.className = "edit-cancel-button";
  cancel.textContent = "Cancel";
  form.append(save, cancel);

  const refreshLimit = attachLimit(textarea, counter, limitMessage, save);

  cancel.addEventListener("click", cancelEdit);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (refreshLimit()) {
      return;  // over the limit: the message already explains why; send nothing
    }
    error.hidden = true;
    error.textContent = "";
    setBusy(save, "Saving...");
    const data = new FormData();
    data.append("description", textarea.value);
    for (const box of checks) {
      if (box.checked) {
        data.append("remove_photos", box.value);
      }
    }
    for (const file of files.files) {
      data.append("photos", file);
    }
    try {
      const response = await fetch("/api/logs/" + encodeURIComponent(log.id), {
        method: "PUT",
        body: data,
      });
      if (!response.ok) {
        // Keep the form (and the user's input) open; do not reload the list.
        error.textContent = await errorMessage(response, "Couldn't update your log");
        error.hidden = false;
        return;
      }
      editing = null;
      await loadLogs();
    } catch (err) {
      error.textContent = networkMessage("Couldn't update your log");
      error.hidden = false;
    } finally {
      clearBusy(save, "Save");
      refreshLimit();
    }
  });

  // Hide (not remove) the normal view so Cancel can restore it untouched.
  const hidden = [...item.children].filter((el) => !el.classList.contains("edit-form"));
  for (const el of hidden) {
    el.hidden = true;
  }
  item.appendChild(form);
  editing = { form, hidden };
}

function renderLogs(logs) {
  editing = null;  // the old items are about to be discarded
  logList.replaceChildren(...logs.map(renderLog));
  emptyMessage.hidden = logs.length > 0;
}

function showError(message) {
  logList.replaceChildren();
  emptyMessage.hidden = true;
  loadError.textContent = message;
  loadError.hidden = false;
}

// Paging: the API has no total, so ask for one extra log; a 6th means an older page exists.
const PAGE_SIZE = 5;
const prevButton = document.getElementById("prev-button");
const nextButton = document.getElementById("next-button");
let currentPage = 0;     // zero-based page that is shown (or was last shown)
let hasNextPage = false;
let loadSeq = 0;         // only the latest request may change the view

function syncPager(loading) {
  prevButton.disabled = loading || currentPage === 0;
  nextButton.disabled = loading || !hasNextPage;
}

async function loadPage(page) {
  const seq = ++loadSeq;
  loadError.hidden = true;
  loadError.textContent = "";
  syncPager(true);
  try {
    const query = "?limit=" + (PAGE_SIZE + 1) + "&offset=" + page * PAGE_SIZE;
    const response = await fetch("/api/logs" + query);
    if (!response.ok) {
      throw new Error("the server returned HTTP " + response.status);
    }
    const logs = await response.json();
    if (!Array.isArray(logs)) {
      throw new Error("the server sent an unexpected response");
    }
    if (seq !== loadSeq) {
      return;
    }
    if (logs.length === 0 && page > 0) {
      await loadPage(page - 1);  // the page emptied (e.g. after a delete): step back
      return;
    }
    currentPage = page;
    hasNextPage = logs.length > PAGE_SIZE;
    renderLogs(logs.slice(0, PAGE_SIZE));
  } catch (err) {
    if (seq !== loadSeq) {
      return;
    }
    let detail = err.message;
    if (err instanceof TypeError) {
      detail = "could not reach the server";
    } else if (err instanceof SyntaxError) {
      detail = "the server sent an unexpected response";
    }
    showError("Couldn't load your logs: " + detail + ". Reload the page or try again later.");
  } finally {
    if (seq === loadSeq) {
      syncPager(false);
    }
  }
}

function loadLogs() {
  return loadPage(currentPage);  // reload the page that is shown
}

prevButton.addEventListener("click", () => {
  if (!prevButton.disabled && currentPage > 0) {
    loadPage(currentPage - 1);
  }
});
nextButton.addEventListener("click", () => {
  if (!nextButton.disabled && hasNextPage) {
    loadPage(currentPage + 1);
  }
});

const logForm = document.getElementById("log-form");
const formError = document.getElementById("form-error");
const saveButton = document.getElementById("save-button");

function showFormError(message) {
  formError.textContent = message;
  formError.hidden = false;
}

// Next-step hints for the known API detail strings (matched case-insensitively).
const ERROR_HINTS = [
  ["invalid or corrupt image", "Choose a JPG, PNG or WEBP photo and try again."],
  ["photo exceeds 5 mib", "Choose a smaller photo, under 5 MB, and try again."],
  ["a log needs between 1 and 5 photos", "Keep between 1 and 5 photos and try again."],
  ["description must be at most 200 characters",
    "Shorten your description to 200 characters or fewer and try again."],
  ["log not found","It may already be deleted; reload the page."],
];

function failureMessage(prefix, detail) {
  const text = String(detail).trim().replace(/\.+$/, "");
  const lower = text.toLowerCase();
  const known = ERROR_HINTS.find(([key]) => lower.includes(key));
  return prefix + ": " + text + ". " + (known ? known[1] : "Please try again.");
}

function networkMessage(prefix) {
  return prefix + ": could not reach the server. Check your connection and try again.";
}

async function errorMessage(response, prefix) {
  // API errors look like {"detail": "..."}; fall back to the status code.
  try {
    const body = await response.json();
    if (typeof body.detail === "string" && body.detail.trim()) {
      return failureMessage(prefix, body.detail);
    }
  } catch (err) {
    // not JSON
  }
  return failureMessage(prefix, "the server returned HTTP " + response.status);
}

// In-flight buttons are disabled (no double submit) and marked aria-busy so
// CSS can show progress; clearBusy restores the original label.
function setBusy(button, label) {
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  button.textContent = label;
}

function clearBusy(button, label) {
  button.disabled = false;
  button.removeAttribute("aria-busy");
  button.textContent = label;
}

const refreshCreateLimit = attachLimit(
  document.getElementById("description"),
  document.getElementById("description-count"),
  document.getElementById("description-limit"),
  saveButton,
);

async function saveLog(event) {
  event.preventDefault();
  if (refreshCreateLimit()) {
    return;  // over the limit: the message already explains why; send nothing
  }
  formError.hidden = true;
  formError.textContent = "";
  setBusy(saveButton, "Saving...");
  try {
    const response = await fetch("/api/logs", {
      method: "POST",
      body: new FormData(logForm),
    });
    if (!response.ok) {
      showFormError(await errorMessage(response, "Couldn't save your log"));
      return;
    }
    logForm.reset();
    refreshCreateLimit();  // reset fires no input event
    await loadPage(0);  // a new log is the newest, so show page 1
  } catch (err) {
    showFormError(networkMessage("Couldn't save your log"));
  } finally {
    clearBusy(saveButton, "Save");
    refreshCreateLimit();
  }
}

logForm.addEventListener("submit", saveLog);

loadLogs();
