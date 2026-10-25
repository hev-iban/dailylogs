# T002 request: create-log endpoint (description + photo upload) with validation

Project root: C:/Users/Ivan/Desktop/A-Finals. Windows host; Python 3.12.6.
The user builds in explicit stages. Implement ONLY this stage.

## Current state
The project is an EMPTY skeleton the user defined. All these files exist and are empty:
backend/main.py, backend/database.py, backend/models.py, backend/routes.py,
backend/tests/test_logs.py, frontend/index.html, frontend/style.css, frontend/app.js,
Dockerfile, compose.yaml, .dockerignore, .gitignore. uploads/ is an empty folder.
requirements.txt already lists: fastapi, uvicorn, python-multipart, pillow, httpx, pytest.
Do not create files or folders outside this tree (no conftest.py, no __init__.py unless strictly
required for imports to work, in which case record why). README.md/specs.md exist; do not edit them in this stage.

Stack (binding): Python + FastAPI, SQLite (descriptions, timestamps, image paths),
photos on disk in uploads/, pytest.
Per-file roles: main.py = app creation/wiring; database.py = SQLite connection/schema;
models.py = data shapes/constants; routes.py = API endpoints; tests/test_logs.py = tests.

## Scope of this stage
Create a log: one request carrying a description and photos. Saved log gets created_at and
updated_at (equal on create), stored in SQLite with its photo paths. Return the created log.
OUT OF SCOPE: list, get, edit, delete endpoints, frontend, Dockerfile/compose, search.

## Binding rules (from the user)
| Rule | Constraint |
| Description | Required; cannot be null, empty, or whitespace-only |
| Minimum photos | 1 per request |
| Maximum photos | 5 per request |
| Maximum file size | 5 MB per photo |
| Allowed formats | JPEG, PNG, WEBP (extensions .jpg .jpeg .png .webp) |
| Storage location | Every accepted image is saved under uploads/ (the project's uploads folder) |
| Invalid file | Reject unsupported file types and invalid image content |
| Oversized file | Reject any photo larger than 5 MB |
| Invalid request | Return an appropriate HTTP error |
| Partial uploads | If any photo fails validation, leave no files from that request behind |
Unique generated filenames so nothing is overwritten; the original filename must not be able to place a file outside uploads/.

## Binding status codes
| Valid request and photos saved | 201 Created |
| Missing or invalid description | 422 |
| No photos or more than 5 photos | 422 |
| Unsupported file type or corrupt image | 422 |
| Photo exceeds 5 MiB (5*1024*1024 bytes) | 413 |
| Request body exceeds a configured limit | 413 |
| Unexpected server or disk error | 500 |

Tests must run against an isolated temporary DB and uploads folder, never the real ones.
