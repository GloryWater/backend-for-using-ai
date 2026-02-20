# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

import logging

from fastapi import APIRouter, HTTPException

from src.database.crud import validate_license
from src.dependencies import AI, DbSession
from src.schemas import AIRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI"])


@router.post("/edit")
async def edit_ad(req: AIRequest, ai: AI, db: DbSession):
    is_valid, msg, _status = await validate_license(db, req.key, req.hwid)
    if not is_valid:
        logger.warning(
            "AI edit denied: key=%s***, reason=%s, text_preview=%s",
            req.key[-4:] if len(req.key) > 4 else req.key,
            msg,
            req.text[:50] if req.text else "empty",
        )
        raise HTTPException(status_code=403, detail=msg)

    result = await ai.edit_text(req.text)
    logger.info(
        "AI edit completed: key=%s***, input_len=%d, output_len=%d",
        req.key[-4:] if len(req.key) > 4 else req.key,
        len(req.text),
        len(result),
    )
    return {"result": result}
