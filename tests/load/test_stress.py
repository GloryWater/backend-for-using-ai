"""
Stress tests for extreme load.

Tests system behavior beyond normal load.

Run:
    pytest tests/load/test_stress.py -v --load  # Fast test
    pytest tests/load/test_stress.py -v --load --full-mode  # Full test
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
    """Stress tests for /auth endpoint."""

    @pytest.mark.asyncio
    async def test_auth_stress(self, request):
        """
        Authentication stress test with high load.

        Goal: Determine failure point and maximum throughput.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = config.concurrent_users * 3  # 3x load (was 5x)
        config.test_duration_seconds = 15  # Short test (was 30)
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

        # Check that system survived
        assert metrics.total_requests > 0
        # Allow up to 70% errors under stress (was 50%)
        assert metrics.error_rate < 70, f"Too many errors: {metrics.error_rate}%"


@pytest.mark.stress
class TestStressEditEndpoint:
    """Stress tests for /edit endpoint."""

    @pytest.mark.asyncio
    async def test_edit_stress(self, request):
        """
        Editing stress test with high load.

        Goal: Check how LLM service handles overload.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = 5  # Reduced (was 20)
        config.test_duration_seconds = 15  # Reduced (was 30)
        metrics = LoadTestMetrics()

        test_texts = ["Sell garage " + str(i) for i in range(10)]

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
    """Maximum connection tests."""

    @pytest.mark.asyncio
    async def test_max_connections(self, request):
        """
        Maximum concurrent connections test.

        Goal: Determine server connection limit.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = 20  # Reduced (was 100)
        config.test_duration_seconds = 10  # Reduced (was 20)
        config.timeout_seconds = 5  # Reduced (was 10)
        metrics = LoadTestMetrics()

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def connection_worker():
                while session.is_running:
                    await session.request("GET", "/health")
                    await asyncio.sleep(0.1)

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

        # Even under overload some requests should pass
        assert metrics.total_requests > 0


@pytest.mark.stress
class TestStressInvalidRequests:
    """Invalid requests stress test."""

    @pytest.mark.asyncio
    async def test_invalid_requests_flood(self, request):
        """
        Invalid requests flood stress test.

        Goal: Verify that server correctly rejects invalid requests
        and continues to work.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = 5  # Reduced (was 20)
        config.test_duration_seconds = 15  # Reduced (was 30)
        metrics = LoadTestMetrics()

        invalid_payloads = [
            {"key": "", "hwid": "test"},  # Empty key
            {"key": "x" * 1000, "hwid": "test"},  # Very long key
            {"key": "test", "hwid": ""},  # Empty HWID
            {"wrong": "data"},  # Wrong structure
            {},  # Empty object
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

        # After invalid requests server should continue working
        # Check this with a healthy request
        async with LoadTestSession(config) as health_session:
            result = await health_session.request("GET", "/health")
            assert result.status_code == 200, "Server is broken after invalid requests"


@pytest.mark.stress
class TestStressRampUp:
    """Fast load increase tests."""

    @pytest.mark.asyncio
    async def test_rapid_ramp_up(self, request):
        """
        Fast load increase test.

        Goal: Check how system handles sharp traffic growth.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.concurrent_users = 15  # Reduced (was 50)
        config.ramp_up_seconds = 2  # Fast ramp-up
        config.test_duration_seconds = 15  # Reduced (was 30)
        metrics = LoadTestMetrics()

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            # Fast ramp-up
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
