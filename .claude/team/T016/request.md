# T016 request

User: "lets add CI add .github/workflows in the directory for github action tab"

Clarified scope (user chose): a working test workflow, not structure only.
- Add `.github/workflows/tests.yml` so it appears in the repo's GitHub Actions tab (remote: github.com/hev-iban/dailylogs).
- Run the existing pytest suite (`backend/tests`) on push and pull_request to `main`.
- Tests require PostgreSQL via `TEST_DATABASE_URL` whose db name ends in `_test` (see backend/tests/conftest.py and README.md "Test" section). Use a Postgres service container.
- Python 3.12 (local dev uses 3.12.6). Install from pinned requirements.txt.
- Only this one new file. No other files, no README change unless strictly needed, no lint/format jobs, no Docker (Dockerfile and compose.yaml are empty).
- Never commit or push; the workflow cannot be run on GitHub by us, so verification is local (YAML validity, and running the same steps locally against a Postgres if available, on a port that is not 8000 and a db ending in _test; never touch the user's real `dailylog` database or uploads/).
