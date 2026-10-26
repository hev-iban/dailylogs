# DailyLog Specification

DailyLog is a personal journaling web application for recording daily activities,
experiences, and memories with photos and written descriptions. It is single-user and
runs locally, so there is no login or logout.

## Technology

| Layer | Choice |
|---|---|
| Backend | Python, FastAPI (API), Pydantic (description validation), Pillow (image checks) |
| Database | PostgreSQL (descriptions, timestamps, photo paths) |
| Photo storage | `uploads/` folder on disk (a named volume when run with Docker) |
| Frontend | HTML, CSS, JavaScript, talking to the backend over HTTP |
| Tests | pytest |

## Core features

1. **Create a log**: a description and 1 to 5 photos are required.
2. **View logs**: all entries, newest first, each showing its date, description, and photos.
3. **Edit a log**: change the description, remove photos, and add photos in one request.
4. **Delete a log**: removes the entry and its photo files from disk.
5. **Automatic timestamps**: `created_at` is set on create; `updated_at` is set on create
   and refreshed on every successful edit. `created_at` never changes.
6. **Persistent storage**: entries and photos survive application restarts.

## Validation rules

| Rule | Limit | Response when broken |
|---|---|---|
| Description | Required, not blank; 1 to 200 characters after trimming surrounding spaces | 422 |
| Photos per log | At least 1, at most 5 (applies on create and to the result of an edit) | 422 |
| Extensions | `.jpg`, `.jpeg`, `.png`, `.webp` (case-insensitive) | 422 |
| File content | Must be a real, readable JPEG, PNG or WEBP image; empty files are rejected | 422 |
| Photo size | At most 5 MiB (5,242,880 bytes) per photo; exactly 5 MiB is accepted | 413 |
| Request size | At most 26 MiB per request | 413 |

The extension and the real format do not have to match: a PNG named `photo.jpg` is
accepted and stored as `.png`, because the stored extension comes from the detected format.

The description is stored trimmed. Its length is counted in characters, so an emoji or an
accented letter counts as one.

When a request breaks several rules, the response follows this order: request over 26 MiB
(413), then, on edit, an unknown log id (404), then request shape such as description, photo
count or extension (422), then a photo over 5 MiB (413), then empty, corrupt or unsupported
image content (422).

Additional guarantees:

- One invalid photo rejects the whole request; nothing is stored.
- A rejected edit changes neither the log nor any files.
- If saving fails midway (disk or database error), every file written by that request is
  removed and the response is 500.
- Every stored photo gets a unique generated filename (UUID), so uploads never overwrite
  each other and the original filename cannot place a file outside `uploads/`.
- Photos removed by an edit, and all photos of a deleted log, are deleted from disk. Only
  files directly inside `uploads/` are ever removed.

## API

Create and edit take `multipart/form-data`. All other responses are JSON, except
`DELETE`, which returns no body.

| Method | Path | Purpose | Success |
|---|---|---|---|
| `GET` | `/` | The web page | 200 |
| `GET` | `/static/{file}` | Frontend files (`style.css`, `app.js`) | 200 |
| `GET` | `/uploads/{file}` | A stored photo | 200 |
| `GET` | `/api/logs` | List all logs, newest first | 200 |
| `POST` | `/api/logs` | Create a log. Fields: `description`, `photos` (1 to 5 files) | 201 |
| `PUT` | `/api/logs/{id}` | Edit a log. Fields: `description`, `remove_photos` (repeatable photo paths), `photos` (new files, optional) | 200 |
| `DELETE` | `/api/logs/{id}` | Delete a log and its photos | 204 |

- An unknown log id returns 404 `log not found`. A non-integer id returns 422.
- On edit, a `remove_photos` value that is not a photo of that log returns 422
  `remove_photos must be photos of this log`.
- Concurrent edits of one log are serialized: an edit locks the log before reading its
  photos, and the lock is held until the edit commits or fails. A later edit is validated
  against the photos committed by the earlier one, so removing a photo the earlier edit
  already removed returns 422 `remove_photos must be photos of this log`, and an edit of a
  log deleted meanwhile returns 404 `log not found` and leaves no new files.
- A missing photo, or any path outside `uploads/`, returns 404.

Errors always have the form `{"detail": "<message>"}`. Examples:

| Status | `detail` |
|---|---|
| 422 | `description is required and cannot be blank` |
| 422 | `description must be at most 200 characters` |
| 422 | `at least 1 photo is required` / `at most 5 photos are allowed` |
| 422 | `a log needs between 1 and 5 photos` (edit) |
| 422 | `photos must be file parts` / `each photo needs a filename` |
| 422 | `remove_photos must be photos of this log` / `remove_photos must be text values` (edit) |
| 422 | `unsupported file type; use jpg, jpeg, png or webp` |
| 422 | `empty file` / `invalid or corrupt image` / `unsupported image format` |
| 413 | `photo exceeds 5 MiB` / `request body too large` |
| 404 | `log not found` |
| 500 | `internal server error` |

Example log:

```json
{
  "id": 1,
  "description": "Hiked to the lake.",
  "photos": ["uploads/3f9c0d...e1.jpg", "uploads/a71b2e...04.png"],
  "created_at": "2026-10-24T08:15:02.123456+00:00",
  "updated_at": "2026-10-24T08:15:02.123456+00:00"
}
```

Photo paths are relative; the page loads them from `/uploads/<file>`. Timestamps are set by
the server in UTC and shown in local time by the frontend. Logs with the same `created_at`
are ordered by higher `id` first.

## Data model

```
logs    (id, description, created_at, updated_at)
photos  (id, log_id -> logs.id ON DELETE CASCADE, path, position)
```

Photos keep the order in which they were uploaded. On edit, kept photos stay in order and
new photos are added after them.

## Frontend behavior

- The page loads all logs when it opens. It shows "No logs yet." when there are none, and a
  message with a next step if they cannot be loaded.
- **New log form**: description and photo picker. A live `N/200` counter shows the
  description length; over 200, a message says how many characters to remove and Save is
  blocked until it is short enough.
- **Edit**: opens an inline form on the post (one post at a time) with the description, a
  Remove checkbox per photo, and a picker for new photos. Cancel restores the post unchanged.
- **Delete**: asks for confirmation first.
- **While saving or deleting**, the button shows "Saving..." or "Deleting..." and cannot be
  pressed again.
- **Errors** say what failed and what to do next, for example
  "Couldn't save your log: invalid or corrupt image. Choose a JPG, PNG or WEBP photo and try
  again." Network failures say the server could not be reached.
- **Light and dark themes**: the page follows the system setting until the theme switch in
  the header is used; the choice is then remembered in the browser.
- Descriptions are always shown as plain text, never as HTML.

## Out of scope for this version

- Search and date filtering (planned for a later stage)
- Getting a single log by id
- Pagination
- Login, logout, or multiple users
