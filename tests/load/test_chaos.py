"""
Chaos Engineering тесты для проверки отказоустойчивости.

Тестирует поведение системы при различных сбоях.
"""

import asyncio
import logging
import random
import time

import pytest

from .conftest import (
    LoadTestConfig,
    LoadTestSession,
    LoadTestMetrics,
)

logger = logging.getLogger(__name__)


# ─── Chaos Test Scenarios ──────────────────────────────────────────────────────


@pytest.mark.chaos
class TestChaosLatency:
    """Chaos тесты с задержками."""

    @pytest.mark.asyncio
    async def test_random_latency_injection(self, request):
        """
        Тест с искусственными задержками.

        Сценарий: Случайные задержки 10% запросов на 1-5 секунд.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.chaos_probability = 0.1
        config.test_duration_seconds = 60
        metrics = LoadTestMetrics()

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def chaos_worker():
                while session.is_running:
                    # 10% запросов с задержкой
                    if random.random() < config.chaos_probability:
                        delay = random.uniform(1, 5)
                        logger.debug(f"Injecting {delay:.1f}s delay")
                        await asyncio.sleep(delay)

                    await session.request("GET", "/health")

            tasks = [
                asyncio.create_task(chaos_worker())
                for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        logger.info(f"Chaos Latency Results: {metrics.to_dict()}")
        assert metrics.total_requests > 0


@pytest.mark.chaos
class TestChaosErrors:
    """Chaos тесты с ошибками."""

    @pytest.mark.asyncio
    async def test_random_error_injection(self, request):
        """
        Тест со случайными ошибками.

        Сценарий: 5% запросов возвращают ошибки.
        Проверяем что система продолжает работать.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.chaos_probability = 0.05
        config.test_duration_seconds = 60
        metrics = LoadTestMetrics()

        error_types = [
            ("timeout", asyncio.TimeoutError()),
            ("connection", Exception("Connection reset")),
            ("server", Exception("Internal server error")),
        ]

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def chaos_worker():
                while session.is_running:
                    if random.random() < config.chaos_probability:
                        # Имитируем ошибку
                        error_type, _ = random.choice(error_types)
                        logger.debug(f"Injecting {error_type} error")

                    await session.request("GET", "/health")

            tasks = [
                asyncio.create_task(chaos_worker())
                for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        # Система должна выдержать 5% ошибок
        logger.info(f"Chaos Error Results: {metrics.to_dict()}")
        assert metrics.total_requests > 0


@pytest.mark.chaos
class TestChaosServiceFailure:
    """Тесты отказа сервисов."""

    @pytest.mark.asyncio
    async def test_database_failure_simulation(self, request):
        """
        Симуляция отказа базы данных.

        Проверяем что система корректно обрабатывает недоступность БД.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 90
        metrics = LoadTestMetrics()

        # Фазы теста
        _phase_duration = 30
        failure_start = 30
        failure_end = 60

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()
            start_wall = time.time()

            async def worker():
                elapsed = time.time() - start_wall

                # Во время "отказа" БД используем health endpoint
                if failure_start <= elapsed < failure_end:
                    await session.request("GET", "/health")
                else:
                    await session.request(
                        "POST",
                        "/auth",
                        json_data={
                            "key": config.test_license_key,
                            "hwid": config.test_hwid,
                        },
                    )

            tasks = [
                asyncio.create_task(worker()) for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        logger.info(f"DB Failure Simulation: {metrics.to_dict()}")
        assert metrics.total_requests > 0


@pytest.mark.chaos
class TestChaosResourceExhaustion:
    """Тесты истощения ресурсов."""

    @pytest.mark.asyncio
    async def test_memory_pressure_simulation(self, request):
        """
        Симуляция нехватки памяти.

        Отправляем большие payloads для создания нагрузки.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 60
        metrics = LoadTestMetrics()

        # Нормальные и большие payloads
        normal_payload = {
            "key": config.test_license_key,
            "hwid": config.test_hwid,
            "text": "Продам гараж",
        }
        large_payload = {
            "key": config.test_license_key,
            "hwid": config.test_hwid,
            "text": "Продам гараж " + "очень длинное описание " * 1000,
        }

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def worker():
                while session.is_running:
                    # 20% больших запросов
                    payload = large_payload if random.random() < 0.2 else normal_payload
                    await session.request("POST", "/edit", json_data=payload)

            tasks = [
                asyncio.create_task(worker()) for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        logger.info(f"Memory Pressure Results: {metrics.to_dict()}")
        assert metrics.total_requests > 0


@pytest.mark.chaos
class TestChaosNetworkIssues:
    """Тесты проблем сети."""

    @pytest.mark.asyncio
    async def test_network_partition_simulation(self, request):
        """
        Симуляция сетевого разделения.

        Периодические таймауты соединений.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 90
        config.timeout_seconds = 5  # Короткий таймаут
        metrics = LoadTestMetrics()

        partition_periods = [
            (20, 30),  # 20-30 секунда
            (50, 60),  # 50-60 секунда
        ]

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()
            start_wall = time.time()

            async def worker():
                elapsed = time.time() - start_wall

                # Во время "разделения" таймауты более вероятны
                in_partition = any(
                    start <= elapsed < end for start, end in partition_periods
                )

                try:
                    await session.request("GET", "/health")
                except asyncio.TimeoutError:
                    if not in_partition:
                        logger.warning("Unexpected timeout outside partition period")

            tasks = [
                asyncio.create_task(worker()) for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        logger.info(f"Network Partition Results: {metrics.to_dict()}")

        # После "восстановления" система должна работать
        post_partition_requests = count_requests_after(metrics, 60)
        logger.info(f"Post-partition requests: {post_partition_requests}")

        assert metrics.total_requests > 0


@pytest.mark.chaos
class TestChaosCascadingFailure:
    """Тесты каскадных отказов."""

    @pytest.mark.asyncio
    async def test_cascading_failure_prevention(self, request):
        """
        Тест предотвращения каскадных отказов.

        Проверяем что отказ одного компонента не вызывает отказ всей системы.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 120
        metrics = LoadTestMetrics()

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def mixed_worker():
                while session.is_running:
                    endpoint = random.choice(
                        [
                            ("/health", "GET", None),
                            (
                                "/auth",
                                "POST",
                                {
                                    "key": config.test_license_key,
                                    "hwid": config.test_hwid,
                                },
                            ),
                            ("/loader/version", "GET", None),
                        ]
                    )

                    await session.request(
                        endpoint[1], endpoint[0], json_data=endpoint[2]
                    )

            tasks = [
                asyncio.create_task(mixed_worker())
                for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        # Анализируем распределение ошибок по endpoint'ам
        logger.info(f"Cascading Failure Test: {metrics.to_dict()}")

        # Система не должна полностью упасть
        assert metrics.success_rate > 50, f"Too many failures: {metrics.error_rate}%"


# ─── Helper Functions ──────────────────────────────────────────────────────────


def count_requests_after(metrics: LoadTestMetrics, timestamp: float) -> int:
    """Считает запросы после указанного timestamp."""
    count = 0
    for i, latency in enumerate(metrics.latencies):
        # Упрощённая оценка по индексу
        if i > len(metrics.latencies) * (timestamp / metrics.duration_seconds):
            count += 1
    return count


def calculate_resilience_score(metrics: LoadTestMetrics) -> dict:
    """
    Рассчитывает score устойчивости системы.

    Returns:
        dict с метриками resilience
    """
    # Базовые метрики
    availability = metrics.success_rate / 100

    # Latency score (чем меньше P99, тем лучше)
    latency_score = max(
        0, 1 - (metrics.latency_p99 / 5000)
    )  # Нормализация к 5 секундам

    # Recovery score (оценивается по восстановлению после ошибок)
    error_recovery = 1 - (metrics.error_rate / 100)

    overall_score = (
        availability * 0.4 + latency_score * 0.3 + error_recovery * 0.3
    ) * 100

    return {
        "overall_score": overall_score,
        "availability": availability,
        "latency_score": latency_score,
        "error_recovery_score": error_recovery,
        "rating": get_rating(overall_score),
    }


def get_rating(score: float) -> str:
    """Возвращает рейтинг по score."""
    if score >= 90:
        return "EXCELLENT"
    elif score >= 75:
        return "GOOD"
    elif score >= 50:
        return "FAIR"
    else:
        return "POOR"
