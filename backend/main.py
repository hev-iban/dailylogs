"""App creation and wiring. Run from backend/: uvicorn main:app"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import database
from models import (DEFAULT_DB_PATH, DEFAULT_UPLOADS_DIR, FRONTEND_DIR,
                    MAX_REQUEST_BYTES, UPLOADS_URL_PREFIX)
from routes import router


class BodyLimitMiddleware:
    """Reject request bodies over max_bytes with 413 (declared or streamed)."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        if declared > self.max_bytes:
            response = JSONResponse({"detail": "request body too large"}, status_code=413)
            await response(scope, receive, send)
            return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise HTTPException(413, "request body too large")
            return message

        await self.app(scope, limited_receive, send)


def create_app(db_path: Path | None = None, uploads_dir: Path | None = None,
               max_request_bytes: int = MAX_REQUEST_BYTES) -> FastAPI:
    db_path = Path(db_path or DEFAULT_DB_PATH)
    uploads_dir = Path(uploads_dir or DEFAULT_UPLOADS_DIR)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        uploads_dir.mkdir(parents=True, exist_ok=True)
        database.init_db(db_path)
        yield

    app = FastAPI(title="Logs API", lifespan=lifespan)
    app.state.db_path = db_path
    app.state.uploads_dir = uploads_dir
    app.add_middleware(BodyLimitMiddleware, max_bytes=max_request_bytes)
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    # check_dir=False: the directory is created in lifespan, possibly after this point.
    app.mount(f"/{UPLOADS_URL_PREFIX}",
              StaticFiles(directory=uploads_dir, check_dir=False), name="uploads")
    return app


app =create_app()
