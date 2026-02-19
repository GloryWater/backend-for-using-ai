import pytest
from httpx import AsyncClient, ASGITransport  # <--- Импортируем ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_read_main():
    # Создаем "мост" к твоему FastAPI приложению
    transport = ASGITransport(app=app)

    # Передаем транспорт, а не app напрямую
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Убедись, что эндпоинт /loader/version реально существует в твоем app!
        # Если нет — замени на "/" или любой другой рабочий GET-запрос.
        response = await ac.get("/loader/version")

    assert response.status_code == 200
