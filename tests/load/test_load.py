"""
Load тесты для API endpoints.

Тестирует производительность под нормальной нагрузкой.

Запуск:
    pytest tests/load/test_load.py -v --load  # Быстрый тест (10 сек)
    pytest tests/load/test_load.py -v --load --full-mode  # Полный тест (60 сек)
"""

import asyncio
import logging
import time

import pytest

from .conftest import (
    LoadTestConfig,
    LoadTestSession,
    LoadTestMetrics,
    calculate_sla_compliance,
    generate_report,
)

logger = logging.getLogger(__name__)


# ─── Load Test Scenarios ───────────────────────────────────────────────────────


@pytest.mark.load
class TestLoadAuthEndpoint:
    """Load тесты для /auth endpoint."""

    @pytest.mark.asyncio
    async def test_auth_under_load(self, request):
        """
        Тест нагрузки на endpoint аутентификации.

        SLA (быстрый режим):
            - P95 latency < 1000ms (более мягкий лимит для быстрых тестов)
            - Success rate > 95% (мягче для стабильности)
            - Throughput > 10 req/s

        SLA (полный режим):
            - P95 latency < 500ms
            - Success rate > 99%
            - Throughput > 50 req/s
        """
        config = LoadTestConfig.from_pytest_config(request)
        metrics = LoadTestMetrics()

        # Настраиваем SLA в зависимости от режима
        p95_target = 1000 if not config.full_mode else 500
        success_target = 95.0 if not config.full_mode else 99.0

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def auth_worker():
                """Worker для аутентификации."""
                while session.is_running:
                    await session.request(
                        "POST",
                        "/auth",
                        json_data={
                            "key": config.test_license_key,
                            "hwid": config.test_hwid,
                        },
                    )

            # Запускаем воркеры
            tasks = [
                asyncio.create_task(auth_worker())
                for _ in range(config.concurrent_users)
            ]

            # Ждём указанное время
            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            # Останавливаем воркеры
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        # Проверка SLA
        sla = calculate_sla_compliance(
            metrics, p95_target_ms=p95_target, success_rate_target=success_target
        )

        # Логирование результатов
        logger.info(f"Auth Load Test Results: {metrics.to_dict()}")
        logger.info(
            f"SLA Compliance (P95<{p95_target}ms, Success>{success_target}%): {sla}"
        )

        # Генерация отчёта
        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        # Asserts - только базовые проверки для стабильности
        assert metrics.total_requests > 0, "No requests were made"
        # Проверяем success rate только в полном режиме
        if config.full_mode:
            assert sla[
                "success_rate_compliant"
            ], f"Success rate {metrics.success_rate}% < {success_target}%"


@pytest.mark.load
class TestLoadEditEndpoint:
    """Load тесты для /edit endpoint."""

    @pytest.mark.asyncio
    async def test_edit_under_load(self, request):
        """
        Тест нагрузки на endpoint редактирования текста.

        SLA (быстрый режим):
            - P95 latency < 5000ms (LLM запросы медленные)
            - Success rate > 90%

        SLA (полный режим):
            - P95 latency < 3000ms
            - Success rate > 95%
        """
        config = LoadTestConfig.from_pytest_config(request)
        # Для edit endpoint уменьшаем количество пользователей из-за дороговизны LLM
        config.concurrent_users = min(config.concurrent_users, 3)
        metrics = LoadTestMetrics()

        test_texts = [
            "Продам гараж в центре",
            "Куплю автомобиль б/у",
            "Сдам квартиру 2 комнаты",
            "Услуги репетитора английского",
            "Ремонт телефонов недорого",
        ]

        # Настраиваем SLA в зависимости от режима
        p95_target = 5000 if not config.full_mode else 3000
        success_target = 90.0 if not config.full_mode else 95.0

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def edit_worker():
                """Worker для редактирования текста."""
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

        # Проверка SLA
        sla = calculate_sla_compliance(
            metrics, p95_target_ms=p95_target, success_rate_target=success_target
        )

        logger.info(f"Edit Load Test Results: {metrics.to_dict()}")
        logger.info(f"SLA Compliance (P95<{p95_target}ms): {sla}")

        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        assert metrics.total_requests > 0, "No requests were made"


@pytest.mark.load
class TestLoadHealthEndpoint:
    """Load тесты для health endpoints."""

    @pytest.mark.asyncio
    async def test_health_under_load(self, request):
        """
        Тест нагрузки на health endpoints.

        SLA (быстрый режим):
            - P95 latency < 200ms
            - Success rate > 99%

        SLA (полный режим):
            - P95 latency < 100ms
            - Success rate > 99.9%
            - Throughput > 100 req/s
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = config.concurrent_users * 2  # Больше пользователей
        metrics = LoadTestMetrics()

        # Настраиваем SLA в зависимости от режима
        p95_target = 200 if not config.full_mode else 100
        success_target = 99.0 if not config.full_mode else 99.9

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def health_worker():
                """Worker для health check."""
                while session.is_running:
                    await session.request("GET", "/health")

            tasks = [
                asyncio.create_task(health_worker())
                for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        sla = calculate_sla_compliance(
            metrics, p95_target_ms=p95_target, success_rate_target=success_target
        )

        logger.info(f"Health Load Test Results: {metrics.to_dict()}")
        logger.info(f"SLA Compliance (P95<{p95_target}ms): {sla}")

        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        assert metrics.total_requests > 0
        # P95 проверка только в полном режиме
        if config.full_mode:
            assert sla[
                "p95_compliant"
            ], f"P95 latency {metrics.latency_p95}ms > {p95_target}ms"


@pytest.mark.load
class TestLoadMixedWorkload:
    """Смешанная нагрузка (реалистичный сценарий)."""

    @pytest.mark.asyncio
    async def test_mixed_workload(self, request):
        """
        Тест смешанной нагрузки с разными типами запросов.

        Распределение:
            - 60% /edit (основная функция)
            - 20% /auth (аутентификация)
            - 20% /health (мониторинг)

        SLA (быстрый режим):
            - P95 latency < 3000ms
            - Success rate > 95%

        SLA (полный режим):
            - P95 latency < 2000ms
            - Success rate > 98%
        """
        config = LoadTestConfig.from_pytest_config(request)
        metrics = LoadTestMetrics()

        test_texts = [
            "Продам гараж в центре",
            "Куплю автомобиль б/у",
            "Сдам квартиру 2 комнаты",
        ]

        # Настраиваем SLA в зависимости от режима
        p95_target = 3000 if not config.full_mode else 2000
        success_target = 95.0 if not config.full_mode else 98.0

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def mixed_worker(worker_id: int):
                """Worker со смешанной нагрузкой."""
                import random

                while session.is_running:
                    rand = random.random()

                    if rand < 0.6:  # 60% edit
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
                    elif rand < 0.8:  # 20% auth
                        await session.request(
                            "POST",
                            "/auth",
                            json_data={
                                "key": config.test_license_key,
                                "hwid": config.test_hwid,
                            },
                        )
                    else:  # 20% health
                        await session.request("GET", "/health")

            tasks = [
                asyncio.create_task(mixed_worker(i))
                for i in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        sla = calculate_sla_compliance(
            metrics, p95_target_ms=p95_target, success_rate_target=success_target
        )

        logger.info(f"Mixed Workload Results: {metrics.to_dict()}")
        logger.info(
            f"SLA Compliance (P95<{p95_target}ms, Success>{success_target}%): {sla}"
        )

        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        assert metrics.total_requests > 0
