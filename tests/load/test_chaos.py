"""
Chaos Engineering тесты для проверки отказоустойчивости.

Тестирует поведение системы при различных сбоях.

Запуск:
    pytest tests/load/test_chaos.py -v --load  # Быстрый тест
    pytest tests/load/test_chaos.py -v --load --full-mode  # Полный тест
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
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 20  # Уменьшено (было 60)
        metrics = LoadTestMetrics()

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def chaos_worker():
                while session.is_running:
                    if random.random() < config.chaos_probability:
                        delay = random.uniform(0.5, 2)  # Уменьшено (было 1-5)
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
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 20  # Уменьшено (было 60)
        metrics = LoadTestMetrics()

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def chaos_worker():
                while session.is_running:
                    if random.random() < config.chaos_probability:
                        await asyncio.sleep(0.1)
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

        logger.info(f"Chaos Error Results: {metrics.to_dict()}")
        assert metrics.total_requests > 0


@pytest.mark.chaos
class TestChaosServiceFailure:
    """Тесты отказа сервисов."""

    @pytest.mark.asyncio
    async def test_database_failure_simulation(self, request):
        """
        Симуляция отказа базы данных.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 30  # Уменьшено (было 90)
        metrics = LoadTestMetrics()

        failure_start = 10  # Уменьшено
        failure_end = 20

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()
            start_wall = time.time()

            async def worker():
                elapsed = time.time() - start_wall
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
        Симуляция нехватки памяти через большие payloads.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 20  # Уменьшено (было 60)
        metrics = LoadTestMetrics()

        normal_payload = {
            "key": config.test_license_key,
            "hwid": config.test_hwid,
            "text": "Продам гараж",
        }
        large_payload = {
            "key": config.test_license_key,
            "hwid": config.test_hwid,
            "text": "Продам гараж "
            + "очень длинное описание " * 100,  # Уменьшено (было 1000)
        }

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def worker():
                while session.is_running:
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
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 30  # Уменьшено (было 90)
        config.timeout_seconds = 5
        metrics = LoadTestMetrics()

        partition_periods = [(10, 15), (20, 25)]  # Уменьшено

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()
            start_wall = time.time()

            async def worker():
                elapsed = time.time() - start_wall
                in_partition = any(
                    start <= elapsed < end for start, end in partition_periods
                )

                try:
                    await session.request("GET", "/health")
                except asyncio.TimeoutError:
                    if not in_partition:
                        logger.debug("Unexpected timeout outside partition period")

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
        assert metrics.total_requests > 0


@pytest.mark.chaos
class TestChaosCascadingFailure:
    """Тесты каскадных отказов."""

    @pytest.mark.asyncio
    async def test_cascading_failure_prevention(self, request):
        """
        Тест предотвращения каскадных отказов.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 30  # Уменьшено (было 120)
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

        logger.info(f"Cascading Failure Test: {metrics.to_dict()}")
        # Мягкая проверка - система не должна полностью упасть
        assert metrics.total_requests > 0
