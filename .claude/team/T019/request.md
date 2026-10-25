# T019 request

User: "lets do dockerfile and compose" (checklist item 4: "Fill in the Dockerfile and Compose. The Compose file should start the API and Postgres. The uploads folder needs a volume so photos survive restarts, the same as the database.")

Context found by orchestrator:
- Dockerfile, compose.yaml, .dockerignore exist at repo root and are EMPTY. README.md lines 123-124 list them as "Not set up yet".
- App: backend/main.py, run from backend/ as `uvicorn main:app`. Needs DATABASE_URL (refuses to start without it). Creates tables on startup (database.init_db). Uploads dir defaults to models.DEFAULT_UPLOADS_DIR = <project root>/uploads; frontend served from <project root>/frontend. Check backend/models.py for the exact paths so the container layout matches (backend/ and frontend/ are siblings under the project root; uploads/ is at project root).
- requirements.txt at repo root, exact pins (fastapi==0.162.0, uvicorn==0.29, psycopg[binary]==3.3.6, ...).
- CI (.github/workflows/tests.yml) uses Python 3.12 and postgres:17. Match those versions.
- .gitignore ignores .env, .venv/, uploads/, .claude/.
- Checklist item 1: no new features. No new Python dependencies.

Goal:
- Dockerfile: builds the API image (Python 3.12 slim, install requirements.txt, copy backend/ and frontend/, run uvicorn bound to 0.0.0.0). Keep it simple; no multi-stage unless needed.
- compose.yaml: two services, api and Postgres 17. api waits for Postgres to be healthy (pg_isready healthcheck + depends_on condition: service_healthy). Named volumes for the Postgres data AND for the uploads folder so both survive `docker compose down` / restarts.
- .dockerignore: keep .venv, .git, .claude, uploads, __pycache__, .env, etc. out of the build context.
- Credentials: do not hard-code real secrets in committed files. Planner decides the approach (e.g. ${VAR:-default} with a local-dev default, or env_file .env) and justifies it.
- Host ports: the user runs their own dev server on host port 8000 and a local Postgres on host 5432. Planner decides the host port mapping for api and whether to publish Postgres at all; avoid conflicts with 8000 and 5432 by default, or ask.
- Update the two README rows ("Not set up yet") and add a short "Run with Docker" section only if that stays small. No other doc changes.
- If a blocking choice remains, ask the user via clarifications rather than guessing.

Safety:
- Never touch the user's local Postgres data or the `dailylog` database; never use host ports 8000 or 5432; never touch the repo's uploads/ folder or .venv.
- Verifier: run compose with a distinct project name (e.g. `docker compose -p t019verify ...`) and only remove containers/volumes/images belonging to that project. Never run `docker system prune`, `docker volume prune`, or remove anything not created for this task.
- Scratchpad for temp files: C:\Users\Ivan\AppData\Local\Temp\claude\C--Users-Ivan-Desktop-A-Finals\06ed2e94-8e36-4da6-bfa7-5e6605d893ff\scratchpad
- Never commit or push; the user commits themselves.
