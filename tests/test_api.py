import pytest
from httpx import AsyncClient
from src.main import app  # Твой FastAPI app


@pytest.mark.asyncio
async def test_read_main():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/loader/version")  # Пример твоего эндпоинта
    assert response.status_code == 200
