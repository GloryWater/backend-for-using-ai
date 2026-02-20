"""
Spike тесты для проверки реакции на резкие скачки нагрузки.

Тестирует как система справляется с внезапными всплесками трафика.
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

        Сценарий:
            1. Базовая нагрузка (5 пользователей) - 30 секунд
            2. Резкий скачок (50 пользователей) - 10 секунд
            3. Возврат к базовой нагрузке - 30 секунд

        Цель: Проверить восстановление после пика.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 70  # 30 + 10 + 30
        metrics = LoadTestMetrics()

        baseline_users = 5
        spike_users = config.spike_users
        spike_start = 30
        spike_end = 40

        # phase_metrics = {
        #     "pre_spike": LoadLoadTestMetrics(),
        #     "spike": LoadLoadTestMetrics(),
        #     "post_spike": LoadLoadTestMetrics(),
        # }

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
                """Контроллер трафика для управления количеством воркеров."""
                nonlocal active_workers
                current_phase = "pre_spike"
                target_users = baseline_users

                while session.is_running:
                    elapsed = time.time() - start_time

                    # Определение фазы
                    if elapsed < spike_start:
                        new_phase = "pre_spike"
                        new_target = baseline_users
                    elif elapsed < spike_end:
                        new_phase = "spike"
                        new_target = spike_users
                    else:
                        new_phase = "post_spike"
                        new_target = baseline_users

                    # Изменение количества воркеров
                    if new_phase != current_phase or new_target != target_users:
                        current_phase = new_phase
                        target_users = new_target

                        # Добавляем или удаляем воркеры
                        if len(active_workers) < target_users:
                            for _ in range(target_users - len(active_workers)):
                                task = asyncio.create_task(worker())
                                active_workers.append(task)
                                logger.info(
                                    f"Added worker, total: {len(active_workers)}"
                                )

                        elif len(active_workers) > target_users:
                            # Отменяем лишние
                            to_cancel = active_workers[target_users:]
                            for task in to_cancel:
                                task.cancel()
                            active_workers = active_workers[:target_users]
                            logger.info(
                                f"Removed workers, total: {len(active_workers)}"
                            )

                    await asyncio.sleep(1)

            controller_task = asyncio.create_task(traffic_controller())

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            # Отменяем все воркеры
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

        # Проверки
        assert metrics.total_requests > 0
        # После пика система должна восстановиться
        assert (
            metrics.error_rate < 50
        ), f"High error rate after spike: {metrics.error_rate}%"


@pytest.mark.spike
class TestSpikeRecovery:
    """Тесты восстановления после пика."""

    @pytest.mark.asyncio
    async def test_recovery_time(self, request):
        """
        Тест времени восстановления после пиковой нагрузки.

        Измеряет сколько времени требуется системе для возврата
        к нормальной производительности после пика.
        """
        config = LoadTestConfig.from_pytest_config(request)
        metrics = LoadTestMetrics()

        baseline_users = 5
        spike_users = 50
        spike_duration = 10

        latency_history = []
        error_history = []

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()
            start_wall = time.time()

            async def worker():
                while session.is_running:
                    result = await session.request(
                        "POST",
                        "/auth",
                        json_data={
                            "key": config.test_license_key,
                            "hwid": config.test_hwid,
                        },
                    )
                    latency_history.append(
                        (time.time() - start_wall, result.latency_ms)
                    )
                    if result.status_code >= 500:
                        error_history.append(time.time() - start_wall)

            # Базовая нагрузка
            tasks = [asyncio.create_task(worker()) for _ in range(baseline_users)]
            await asyncio.sleep(20)

            # Пик
            for _ in range(spike_users - baseline_users):
                tasks.append(asyncio.create_task(worker()))
            await asyncio.sleep(spike_duration)

            # Возврат к базе
            for task in tasks[baseline_users:]:
                task.cancel()
            tasks = tasks[:baseline_users]

            # Измеряем восстановление
            _recovery_start = time.time()
            await asyncio.sleep(30)

            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        # Анализ времени восстановления
        recovery_time = analyze_recovery_time(
            latency_history, error_history, spike_duration
        )

        logger.info(f"Recovery Test Results: {metrics.to_dict()}")
        logger.info(f"Recovery Time: {recovery_time}")

        assert metrics.total_requests > 0


@pytest.mark.spike
class TestSpikeAuthEndpoint:
    """Spike тесты для /auth endpoint."""

    @pytest.mark.asyncio
    async def test_auth_spike(self, request):
        """
        Spike тест аутентификации.

        Резкий всплеск запросов аутентификации.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = config.spike_users
        config.test_duration_seconds = 15  # Короткий интенсивный тест
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

        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        assert metrics.total_requests > 0


@pytest.mark.spike
class TestSpikeEditEndpoint:
    """Spike тесты для /edit endpoint."""

    @pytest.mark.asyncio
    async def test_edit_spike(self, request):
        """
        Spike тест редактирования.

        Резкий всплеск AI запросов (дорогая операция).
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = 20  # Ограничено из-за дороговизны LLM
        config.test_duration_seconds = 20
        metrics = LoadTestMetrics()

        test_texts = [f"Продам гараж {i}" for i in range(20)]

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

        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        assert metrics.total_requests > 0


# ─── Helper Functions ──────────────────────────────────────────────────────────


def analyze_recovery_time(
    latency_history: list[tuple[float, float]],
    error_history: list[float],
    spike_end_time: float,
) -> dict:
    """
    Анализирует время восстановления системы.

    Args:
        latency_history: Список (время, latency)
        error_history: Список времен ошибок
        spike_end_time: Время окончания пика

    Returns:
        dict с метриками восстановления
    """
    if not latency_history:
        return {"recovery_time_seconds": None, "status": "no_data"}

    # Находим baseline latency (до пика)
    pre_spike_latencies = [lat for t, lat in latency_history if t < spike_end_time - 10]
    if not pre_spike_latencies:
        return {"recovery_time_seconds": None, "status": "no_baseline"}

    baseline_avg = sum(pre_spike_latencies) / len(pre_spike_latencies)

    # Находим когда latency вернулась к baseline после пика
    post_spike_data = [(t, lat) for t, lat in latency_history if t > spike_end_time]

    recovery_time = None
    for t, lat in post_spike_data:
        if lat <= baseline_avg * 1.2:  # В пределах 20% от baseline
            recovery_time = t - spike_end_time
            break

    # Последняя ошибка
    last_error_time = max(error_history) if error_history else spike_end_time

    return {
        "recovery_time_seconds": recovery_time,
        "baseline_latency_ms": baseline_avg,
        "last_error_time": last_error_time - spike_end_time,
        "status": "recovered" if recovery_time else "not_recovered",
    }
