# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

import json
import logging
import os

import aiofiles
from fastapi import APIRouter

from src.config import settings
from src.database.crud import validate_license
from src.dependencies import DbSession
from src.schemas import AuthRequest, AuthResponse, UpdateResponse
from src.utils.crypto import encrypt_and_encode

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Auth"])


@router.post("/auth", response_model=AuthResponse)
async def authenticate(req: AuthRequest, db: DbSession):
    is_valid, msg, _status = await validate_license(db, req.key, req.hwid)
    if not is_valid:
        logger.warning(
            "Auth failed: key=%s***, reason=%s",
            req.key[-4:] if len(req.key) > 4 else req.key,
            msg,
        )
        return AuthResponse(status="error", message=msg)

    if not os.path.exists(settings.SCRIPT_PATH):
        logger.error("Script file not found: %s", settings.SCRIPT_PATH)
        return AuthResponse(status="error", message="Script missing")

    try:
        with open(settings.SCRIPT_PATH, "rb") as f:
            script_bytes = f.read()

        encoded = encrypt_and_encode(script_bytes, req.key)
        logger.info(
            "Auth successful: key=%s***, script_size=%d bytes",
            req.key[-4:] if len(req.key) > 4 else req.key,
            len(script_bytes),
        )
        return AuthResponse(status="success", script_bytes=encoded)

    except IOError as e:
        logger.exception("Error reading script file: %s", e)
        return AuthResponse(status="error", message="Internal error")


@router.get("/loader/version", response_model=UpdateResponse)
async def check_loader_version():
    async with aiofiles.open(settings.LOADER_VERSION_FILE, "r", encoding="utf-8") as f:
        data = json.loads(await f.read())
    return UpdateResponse(version=data["version"], url=data["url"])
