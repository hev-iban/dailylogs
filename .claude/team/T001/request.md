# T001 request: build DailyLog (v1)

Project root: C:/Users/Ivan/Desktop/A-Finals (app code goes here, NOT under .claude/)

## Overview
DailyLog is a personal journaling web app for documenting daily activities with photos and
written descriptions. Single user, no login/logout.

## Core features
- Create a log: description required, at least 1 photo, at most 5 photos.
- View logs: previous entries with photos, description, and dates.
- Edit logs: update description and photos (add/remove), 1..5 photo rule still applies.
- Delete logs: remove the entry AND its image files on disk.
- Automatic timestamps.
- Persistent storage across application restarts.

## Binding user decisions
Stack:
- Python + FastAPI (backend API and request validation)
- SQLite (log descriptions, timestamps, image paths)
- HTML, CSS, JavaScript frontend, talking to backend via HTTP requests
- pytest for API endpoint and validation tests
- uploads/ folder stores uploaded photos

Timestamps: keep both created_at (set automatically on create) and updated_at (most recent edit).

Photos:
- min 1, max 5 per log
- allowed formats: JPG, JPEG, PNG, WEBP
- max 5 MB per photo
- generate unique filenames so nothing is overwritten
- reject invalid files and requests exceeding limits

Display:
- newest first (reverse chronological), simple list
- each entry shows date, description, photos
- create, view, edit, delete from the UI
- search / date filter is OUT OF SCOPE for now (later stage)
