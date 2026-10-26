"""API endpoints.

Status precedence (deterministic): body over limit 413 > request-shape 422
(description, photo count, non-file part, missing filename, extension) >
oversized photo 413 > empty/corrupt/disallowed-format content 422 > 500.

Extension/content policy: the extension must be allowed, and the real image
format (detected by Pillow) must be JPEG/PNG/WEBP. They need not match; the
stored extension is derived from the detected format.
"""
import io
import logging
import os
import uuid
import warnings
from contextlib import closing
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from PIL import Image
from pydantic import ValidationError
from starlette.datastructures import UploadFile

import database
from models import (ALLOWED_EXTENSIONS, ALLOWED_FORMATS, DEFAULT_LIST_LIMIT,
                    MAX_DESCRIPTION_CHARS, MAX_LIST_LIMIT, MAX_LIST_OFFSET,
                    MAX_PHOTO_BYTES,
                    MAX_PHOTOS, MIN_PHOTOS, UPLOADS_URL_PREFIX, DescriptionIn, LogOut)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def _validate_description(value) -> str:
    """Validate with DescriptionIn; map its errors to the contract's plain-string details."""
    try:
        return DescriptionIn.model_validate({"description": value}).description
    except ValidationError as exc:
        if any(e["type"] == "string_too_long" for e in exc.errors()):
            raise HTTPException(
                422, f"description must be at most {MAX_DESCRIPTION_CHARS} characters")
        raise HTTPException(422, "description is required and cannot be blank")


def _extension(filename: str) -> str:
    # Treat both separators as separators regardless of OS; only the suffix is used.
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    return os.path.splitext(base)[1].lower()


def _validate_files(items: list, minimum: int = MIN_PHOTOS) -> list[UploadFile]:
    if len(items) < minimum:
        raise HTTPException(422, "at least 1 photo is required")
    if len(items) > MAX_PHOTOS:
        raise HTTPException(422, f"at most {MAX_PHOTOS} photos are allowed")
    for item in items:
        if not isinstance(item, UploadFile):
            raise HTTPException(422, "photos must be file parts")
        if not item.filename:
            raise HTTPException(422, "each photo needs a filename")
        if _extension(item.filename) not in ALLOWED_EXTENSIONS:
            raise HTTPException(422, "unsupported file type; use jpg, jpeg, png or webp")
    return items


async def _read_all(files: list[UploadFile]) -> list[bytes]:
    blobs = []
    for f in files:
        data = await f.read(MAX_PHOTO_BYTES + 1)
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(413, "photo exceeds 5 MiB")
        blobs.append(data)
    return blobs


def _detect_extensions(blobs: list[bytes]) -> list[str]:
    exts = []
    for data in blobs:
        if not data:
            raise HTTPException(422, "empty file")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")  # decompression-bomb warning -> error
                with Image.open(io.BytesIO(data)) as img:
                    fmt = img.format
                    img.load()  # full decode catches truncated/corrupt data
        except Exception:
            raise HTTPException(422, "invalid or corrupt image")
        if fmt not in ALLOWED_FORMATS:
            raise HTTPException(422, "unsupported image format")
        exts.append(ALLOWED_FORMATS[fmt])
    return exts


def _store(database_url, uploads_dir, description, blobs, exts) -> dict:
    """Write files then insert the row; on any failure remove every file written."""
    written = []
    try:
        uploads_dir.mkdir(parents=True, exist_ok=True)
        names = []
        for data, ext in zip(blobs, exts):
            name = f"{uuid.uuid4().hex}{ext}"
            target = uploads_dir / name
            written.append(target)  # registered before write so partial files are removed
            with open(target, "xb") as fh:
                fh.write(data)
            names.append(f"{UPLOADS_URL_PREFIX}/{name}")
        # Always server-generated.
        now = datetime.now(timezone.utc)
        with closing(database.connect(database_url)) as conn:
            try:
                result = database.insert_log(conn, description, names, now)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return result
    except Exception:
        for path in written:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.exception("could not remove %s", path)
        raise


def _update(database_url, uploads_dir, log_id, description, remove, blobs, exts) -> dict:
    """Validate against the stored photos, write new files, commit, then delete old files.

    Old files go only after the commit; on any failure the new files are removed.
    The log row is locked first (before the photos are read) and the lock is held until
    the commit or the explicit rollback, so concurrent edits of one log run one after
    the other and each sees the photos the previous one committed.
    """
    written = []
    try:
        with closing(database.connect(database_url)) as conn:
            try:
                if not database.lock_log(conn, log_id):
                    raise HTTPException(404, "log not found")
                current = database.get_log(conn, log_id)
                if not remove <= set(current["photos"]):
                    raise HTTPException(422, "remove_photos must be photos of this log")
                kept = [p for p in current["photos"] if p not in remove]
                if not MIN_PHOTOS <= len(kept) + len(blobs) <= MAX_PHOTOS:
                    raise HTTPException(
                        422, f"a log needs between {MIN_PHOTOS} and {MAX_PHOTOS} photos")
                uploads_dir.mkdir(parents=True, exist_ok=True)
                names = []
                for data, ext in zip(blobs, exts):
                    name = f"{uuid.uuid4().hex}{ext}"
                    target = uploads_dir / name
                    written.append(target)  # registered before write so partial files are removed
                    with open(target, "xb") as fh:
                        fh.write(data)
                    names.append(f"{UPLOADS_URL_PREFIX}/{name}")
                now = datetime.now(timezone.utc)
                result = database.update_log(conn, log_id, description, kept + names, now)
                if result is None:
                    raise HTTPException(404, "log not found")
                conn.commit()
            except Exception:
                # Explicit rollback on every early exit and failure: releases the row lock
                # at once instead of relying on the close in the with-block.
                conn.rollback()
                raise
    except Exception:
        for path in written:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.exception("could not remove %s", path)
        raise
    for p in current["photos"]:
        if p in remove:
            try:
                (uploads_dir / p.rsplit("/", 1)[-1]).unlink(missing_ok=True)
            except OSError:
                logger.exception("could not remove %s", p)
    return result


def _delete(database_url, uploads_dir, log_id) -> None:
    """Delete the rows and commit, then remove the photo files.

    File removal is best effort: a missing file or an OS error is logged and never
    undoes the delete. Only files directly inside uploads_dir are ever removed.
    """
    with closing(database.connect(database_url)) as conn:
        try:
            paths = database.delete_log(conn, log_id)
            if paths is None:
                raise HTTPException(404, "log not found")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    root = uploads_dir.resolve()
    for p in paths:
        name = p.replace("\\", "/").rsplit("/", 1)[-1]
        target = uploads_dir / name
        try:
            if name in ("", ".", "..") or target.resolve().parent != root:
                logger.error("refusing to remove %s outside uploads", p)
                continue
            os.remove(target)
        except FileNotFoundError:
            pass
        except Exception:
            logger.exception("could not remove %s", p)


def _exists(database_url, log_id) -> bool:
    with closing(database.connect(database_url)) as conn:
        return database.get_log(conn, log_id) is not None


def _list(database_url, limit, offset) -> list[dict]:
    with closing(database.connect(database_url)) as conn:
        return database.list_logs(conn, limit, offset)


@router.get("/logs", response_model=list[LogOut])
async def list_logs(request: Request, limit: int = Query(DEFAULT_LIST_LIMIT, ge=1),
                    offset: int = Query(0, ge=0, le=MAX_LIST_OFFSET)):
    # limit below 1 or non-integer: 422; above the maximum: clamped.
    # offset below 0, non-integer or beyond the database's bigint: 422.
    limit = min(limit, MAX_LIST_LIMIT)
    try:
        return await run_in_threadpool(_list, request.app.state.database_url, limit, offset)
    except Exception:
        logger.exception("list_logs failed")
        return JSONResponse({"detail": "internal server error"}, status_code=500)


@router.post("/logs", status_code=201, response_model=LogOut)
async def create_log(request: Request):
    try:
        async with request.form() as form:
            description = _validate_description(form.get("description"))
            files = _validate_files(form.getlist("photos"))
            blobs = await _read_all(files)
        exts = await run_in_threadpool(_detect_extensions, blobs)
        return await run_in_threadpool(
            _store, request.app.state.database_url, request.app.state.uploads_dir,
            description, blobs, exts)
    except HTTPException:
        raise
    except Exception:
        logger.exception("create_log failed")
        return JSONResponse({"detail": "internal server error"}, status_code=500)


@router.delete("/logs/{log_id}", status_code=204)
async def delete_log(log_id: int, request: Request):
    try:
        await run_in_threadpool(
            _delete, request.app.state.database_url, request.app.state.uploads_dir, log_id)
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception:
        logger.exception("delete_log failed")
        return JSONResponse({"detail": "internal server error"}, status_code=500)


@router.put("/logs/{log_id}", response_model=LogOut)
async def update_log(log_id: int, request: Request):
    try:
        if not await run_in_threadpool(_exists, request.app.state.database_url, log_id):
            raise HTTPException(404, "log not found")
        async with request.form() as form:
            description = _validate_description(form.get("description"))
            remove = form.getlist("remove_photos")
            if not all(isinstance(r, str) for r in remove):
                raise HTTPException(422, "remove_photos must be text values")
            files = _validate_files(form.getlist("photos"), minimum=0)
            blobs = await _read_all(files)
        exts = await run_in_threadpool(_detect_extensions, blobs)
        return await run_in_threadpool(
            _update, request.app.state.database_url, request.app.state.uploads_dir,
            log_id, description, set(remove), blobs, exts)
    except HTTPException:
        raise
    except Exception:
        logger.exception("update_log failed")
        return JSONResponse({"detail": "internal server error"}, status_code=500)
