"""
Stress тесты для проверки предельных нагрузок.

Тестирует поведение системы за пределами нормальной нагрузки.
"""

import asyncio
import logging
import time

import pytest

from .conftest import (
    LoadTestConfig,
    LoadTestSession,
    LoadTestMetrics,
    generate_report,
)

logger = logging.getLogger(__name__)


# ─── Stress Test Scenarios ─────────────────────────────────────────────────────


@pytest.mark.stress
class TestStressAuthEndpoint:
    """Stress тесты для /auth endpoint."""

    @pytest.mark.asyncio
    async def test_auth_stress(self, request):
        """
        Стресс-тест аутентификации с высокой нагрузкой.

        Цель: Определить точку отказа и максимальную пропускную способность.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = config.concurrent_users * 5  # 5x нагрузка
        config.test_duration_seconds = 30  # Короткий тест
        metrics = LoadTestMetrics()

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def auth_worker():
                while session.is_running:
                    await session.request(
                        "POST",
                        "/auth",
                        json_data={
                            "key": config.test_license_key,
                            "hwid": config.test_hwid,
                        },
                    )

            tasks = [
                asyncio.create_task(auth_worker())
                for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        logger.info(f"Auth Stress Results: {metrics.to_dict()}")

        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        # Проверяем что система выжила
        assert metrics.total_requests > 0
        # Допускаем до 50% ошибок при стрессе
        assert metrics.error_rate < 50, f"Too many errors: {metrics.error_rate}%"


@pytest.mark.stress
class TestStressEditEndpoint:
    """Stress тесты для /edit endpoint."""

    @pytest.mark.asyncio
    async def test_edit_stress(self, request):
        """
        Стресс-тест редактирования с высокой нагрузкой.

        Цель: Проверить как LLM сервис справляется с перегрузкой.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = 20  # Много одновременных LLM запросов
        config.test_duration_seconds = 30
        metrics = LoadTestMetrics()

        test_texts = ["Продам гараж " + str(i) for i in range(10)]

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def edit_worker():
                import random

                while session.is_running:
                    text = random.choice(test_texts)
                    await session.request(
                        "POST",
                        "/edit",
                        json_data={
                            "key": config.test_license_key,
                            "hwid": config.test_hwid,
                            "text": text,
                        },
                    )

            tasks = [
                asyncio.create_task(edit_worker())
                for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        logger.info(f"Edit Stress Results: {metrics.to_dict()}")

        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        assert metrics.total_requests > 0


@pytest.mark.stress
class TestStressConcurrentConnections:
    """Тесты на максимальное количество соединений."""

    @pytest.mark.asyncio
    async def test_max_connections(self, request):
        """
        Тест на максимальное количество одновременных соединений.

        Цель: Определить лимит соединений сервера.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = 100  # Очень много соединений
        config.test_duration_seconds = 20
        config.timeout_seconds = 10  # Короткий таймаут
        metrics = LoadTestMetrics()

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def connection_worker():
                while session.is_running:
                    await session.request("GET", "/health")
                    await asyncio.sleep(0.1)  # Небольшая задержка

            tasks = [
                asyncio.create_task(connection_worker())
                for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        logger.info(f"Max Connections Results: {metrics.to_dict()}")

        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        # Даже при перегрузке некоторые запросы должны пройти
        assert metrics.total_requests > 0


@pytest.mark.stress
class TestStressInvalidRequests:
    """Стресс-тест невалидными запросами."""

    @pytest.mark.asyncio
    async def test_invalid_requests_flood(self, request):
        """
        Стресс-тест потоком невалидных запросов.

        Цель: Проверить что сервер корректно отклоняет невалидные запросы
        и продолжает работать.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = 20
        config.test_duration_seconds = 30
        metrics = LoadTestMetrics()

        invalid_payloads = [
            {"key": "", "hwid": "test"},  # Пустой ключ
            {"key": "x" * 1000, "hwid": "test"},  # Очень длинный ключ
            {"key": "test", "hwid": ""},  # Пустой HWID
            {"wrong": "data"},  # Неправильная структура
            "not json",  # Не JSON
            {},  # Пустой объект
        ]

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def invalid_worker():
                import random

                while session.is_running:
                    payload = random.choice(invalid_payloads)
                    await session.request(
                        "POST",
                        "/auth",
                        json_data=payload if isinstance(payload, dict) else None,
                    )

            tasks = [
                asyncio.create_task(invalid_worker())
                for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        logger.info(f"Invalid Requests Results: {metrics.to_dict()}")

        # После невалидных запросов сервер должен продолжать работать
        # Проверим это здоровым запросом
        async with LoadTestSession(config) as health_session:
            result = await health_session.request("GET", "/health")
            assert result.status_code == 200, "Server is broken after invalid requests"


@pytest.mark.stress
class TestStressRampUp:
    """Тесты с быстрым увеличением нагрузки."""

    @pytest.mark.asyncio
    async def test_rapid_ramp_up(self, request):
        """
        Тест быстрого увеличения нагрузки.

        Цель: Проверить как система справляется с резким ростом трафика.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = 50
        config.ramp_up_seconds = 2  # Очень быстрый ramp-up
        config.test_duration_seconds = 30
        metrics = LoadTestMetrics()

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            # Быстрый ramp-up
            tasks = []
            ramp_delay = config.ramp_up_seconds / config.concurrent_users

            for i in range(config.concurrent_users):
                await asyncio.sleep(ramp_delay)
                if not session.is_running:
                    break

                async def worker():
                    while session.is_running:
                        await session.request("GET", "/health")

                tasks.append(asyncio.create_task(worker()))

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        logger.info(f"Rapid Ramp-up Results: {metrics.to_dict()}")

        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        assert metrics.total_requests > 0
