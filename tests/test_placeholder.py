# tests/test_placeholder.py


def test_answer():
    assert 42 == 42


def test_environment_vars():
    import os

    # Проверяем, что CI видит наши переменные окружения
    assert os.getenv("DATABASE_URL") is not None
