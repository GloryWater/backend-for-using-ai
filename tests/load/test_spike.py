"""
Spike тесты для проверки реакции на резкие скачки нагрузки.

Тестирует как система справляется с внезапными всплесками трафика.

Запуск:
    pytest tests/load/test_spike.py -v --load  # Быстрый тест
    pytest tests/load/test_spike.py -v --load --full-mode  # Полный тест
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


# ─── Spike Test Scenarios ──────────────────────────────────────────────────────


@pytest.mark.spike
class TestSpikeTraffic:
    """Spike тесты трафика."""

    @pytest.mark.asyncio
    async def test_sudden_traffic_spike(self, request):
        """
        Тест внезапного скачка трафика.

        Сценарий (быстрый режим):
            1. Базовая нагрузка (3 пользователей) - 10 секунд
            2. Резкий скачок (10 пользователей) - 5 секунд
            3. Возврат к базовой нагрузке - 10 секунд

        Сценарий (полный режим):
            1. Базовая нагрузка (5 пользователей) - 30 секунд
            2. Резкий скачок (50 пользователей) - 10 секунд
            3. Возврат к базовой нагрузке - 30 секунд

        Цель: Проверить восстановление после пика.
        """
        config = LoadTestConfig.from_pytest_config(request)

        # Настраиваем длительности в зависимости от режима
        if config.full_mode:
            baseline_users = 5
            spike_users = config.spike_users
            spike_start = 30
            spike_end = 40
            config.test_duration_seconds = 70
        else:
            baseline_users = 3
            spike_users = config.spike_users // 2
            spike_start = 10
            spike_end = 15
            config.test_duration_seconds = 25

        metrics = LoadTestMetrics()
        start_time = time.time()

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()
            active_workers = []

            async def worker():
                while session.is_running:
                    await session.request("GET", "/health")
                    await asyncio.sleep(0.1)

            async def traffic_controller():
                """Контроллер трафика."""
                nonlocal active_workers
                current_phase = "pre_spike"
                target_users = baseline_users

                while session.is_running:
                    elapsed = time.time() - start_time

                    if elapsed < spike_start:
                        new_phase = "pre_spike"
                        new_target = baseline_users
                    elif elapsed < spike_end:
                        new_phase = "spike"
                        new_target = spike_users
                    else:
                        new_phase = "post_spike"
                        new_target = baseline_users

                    if new_phase != current_phase or new_target != target_users:
                        current_phase = new_phase
                        target_users = new_target

                        if len(active_workers) < target_users:
                            for _ in range(target_users - len(active_workers)):
                                task = asyncio.create_task(worker())
                                active_workers.append(task)
                        elif len(active_workers) > target_users:
                            to_cancel = active_workers[target_users:]
                            for task in to_cancel:
                                task.cancel()
                            active_workers = active_workers[:target_users]

                    await asyncio.sleep(1)

            controller_task = asyncio.create_task(traffic_controller())
            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in active_workers:
                task.cancel()
            controller_task.cancel()
            await asyncio.gather(
                *active_workers, controller_task, return_exceptions=True
            )
            metrics.end_time = time.perf_counter()

        logger.info(f"Spike Test Results: {metrics.to_dict()}")

        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        assert metrics.total_requests > 0
        assert metrics.error_rate < 60, f"High error rate: {metrics.error_rate}%"


@pytest.mark.spike
class TestSpikeAuthEndpoint:
    """Spike тесты для /auth endpoint."""

    @pytest.mark.asyncio
    async def test_auth_spike(self, request):
        """Spike тест аутентификации."""
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = config.spike_users // 2
        config.test_duration_seconds = 10
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

        logger.info(f"Auth Spike Results: {metrics.to_dict()}")
        assert metrics.total_requests > 0


@pytest.mark.spike
class TestSpikeEditEndpoint:
    """Spike тесты для /edit endpoint."""

    @pytest.mark.asyncio
    async def test_edit_spike(self, request):
        """Spike тест редактирования."""
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = 5
        config.test_duration_seconds = 10
        metrics = LoadTestMetrics()
        test_texts = [f"Продам гараж {i}" for i in range(10)]

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

        logger.info(f"Edit Spike Results: {metrics.to_dict()}")
        assert metrics.total_requests > 0
