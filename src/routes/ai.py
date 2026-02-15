from fastapi import APIRouter, HTTPException

from src.database.crud import validate_license
from src.dependencies import AI, DbSession
from src.schemas import AIRequest

router = APIRouter(tags=["AI"])


@router.post("/edit")
async def edit_ad(req: AIRequest, ai: AI, db: DbSession):
    is_valid, msg = await validate_license(db, req.key, req.hwid)
    if not is_valid:
        raise HTTPException(status_code=403, detail=msg)

    result = await ai.edit_text(req.text)
    return {"result": result}
