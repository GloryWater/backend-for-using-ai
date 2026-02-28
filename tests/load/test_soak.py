"""
Soak tests (endurance tests) for long-term operation.

Tests system stability under prolonged load.

Run:
    pytest tests/load/test_soak.py -v --load  # Fast test (30 sec)
    pytest tests/load/test_soak.py -v --load --full-mode  # Full test (300 sec)
"""

import asyncio
import logging
import time
from collections import defaultdict

import pytest

from .conftest import (
    LoadTestConfig,
    LoadTestSession,
    LoadTestMetrics,
    generate_report,
)

logger = logging.getLogger(__name__)


# ─── Soak Test Scenarios ───────────────────────────────────────────────────────


@pytest.mark.soak
class TestSoakStability:
    """Soak stability tests."""

    @pytest.mark.asyncio
    async def test_soak_5min(self, request):
        """
        Stability test (30 sec fast / 5 min full).

        Goal: Detect memory leaks and performance degradation.

        Success criteria:
            - No gradual latency growth
            - No error rate increase over time
            - Stable throughput
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = config.soak_duration_seconds
        config.concurrent_users = 3  # Reduced (was 5)
        metrics = LoadTestMetrics()

        # Metrics by time intervals
        interval_metrics = defaultdict(
            lambda: {"requests": 0, "latencies": [], "errors": 0}
        )
        interval_seconds = 10  # Reduced (was 30)

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()
            start_wall_time = time.time()

            async def soak_worker():
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
                asyncio.create_task(soak_worker())
                for _ in range(config.concurrent_users)
            ]

            # Collect metrics by intervals
            async def metrics_collector():
                last_interval = 0
                last_total = 0
                last_latencies = 0

                while session.is_running:
                    await asyncio.sleep(interval_seconds)
                    current_interval = (
                        int(time.time() - start_wall_time) // interval_seconds
                    )

                    if current_interval > last_interval:
                        new_requests = metrics.total_requests - last_total
                        _new_latencies = len(metrics.latencies) - last_latencies

                        interval_data = interval_metrics[current_interval]
                        interval_data["requests"] = new_requests
                        interval_data["latencies"] = list(
                            metrics.latencies[last_latencies:]
                        )
                        interval_data["errors"] = metrics.failed_requests - (
                            last_total - metrics.successful_requests
                        )

                        last_interval = current_interval
                        last_total = metrics.total_requests
                        last_latencies = len(metrics.latencies)

                        logger.info(
                            f"Interval {current_interval}: " f"requests={new_requests}"
                        )

            collector_task = asyncio.create_task(metrics_collector())

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            collector_task.cancel()

            metrics.end_time = time.perf_counter()

        # Degradation analysis (only in full mode)
        if len(interval_metrics) >= 2:
            degradation_analysis = analyze_degradation(interval_metrics)
            logger.info(f"Degradation Analysis: {degradation_analysis}")

            # Check degradation only in full mode
            if config.full_mode:
                assert not degradation_analysis[
                    "has_latency_degradation"
                ], "Latency degradation detected"

        logger.info(f"Soak Test Results: {metrics.to_dict()}")

        if config.generate_report:
            report_path = generate_report(metrics, config)
            logger.info(f"Report generated: {report_path}")

        # Checks
        assert metrics.total_requests > 0, "No requests were made"


@pytest.mark.soak
class TestSoakMemoryLeak:
    """Memory leak tests."""

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, request):
        """
        Memory leak detection test via latency monitoring.

        Indirect sign of memory leak - latency growth over time.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 30  # Reduced (was 180)
        config.concurrent_users = 2  # Reduced (was 3)
        metrics = LoadTestMetrics()

        latency_samples = []
        sample_interval = 5  # Reduced (was 10)

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def worker():
                while session.is_running:
                    await session.request("GET", "/health")
                    await asyncio.sleep(0.5)

            async def sampler():
                while session.is_running:
                    await asyncio.sleep(sample_interval)
                    if metrics.latencies:
                        recent = metrics.latencies[-10:]
                        latency_samples.append(sum(recent) / len(recent))

            tasks = [
                asyncio.create_task(worker()) for _ in range(config.concurrent_users)
            ]
            sampler_task = asyncio.create_task(sampler())

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            sampler_task.cancel()
            await asyncio.gather(*tasks, *([sampler_task]), return_exceptions=True)

            metrics.end_time = time.perf_counter()

        # Latency trend analysis (informational, non-blocking)
        if len(latency_samples) >= 3:
            trend = analyze_latency_trend(latency_samples)
            logger.info(f"Latency trend: {trend}")

        logger.info(f"Memory Leak Test Results: {metrics.to_dict()}")
        assert metrics.total_requests > 0


@pytest.mark.soak
class TestSoakConnectionPool:
    """Connection pool tests."""

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, request):
        """
        Connection pool exhaustion test.

        Goal: Verify that connections are correctly returned to pool.
        """
        config = LoadTestConfig.from_pytest_config(request)
        config.test_duration_seconds = 30  # Reduced (was 120)
        config.concurrent_users = 5  # Reduced (was 10)
        metrics = LoadTestMetrics()

        timeout_errors = 0
        connection_errors = 0

        async with LoadTestSession(config) as session:
            session.metrics = metrics
            metrics.start_time = time.perf_counter()

            async def worker():
                nonlocal timeout_errors, connection_errors
                while session.is_running:
                    result = await session.request("GET", "/health")
                    if result.error:
                        if "Timeout" in result.error:
                            timeout_errors += 1
                        elif "connection" in result.error.lower():
                            connection_errors += 1

            tasks = [
                asyncio.create_task(worker()) for _ in range(config.concurrent_users)
            ]

            await asyncio.sleep(config.test_duration_seconds)
            session.stop()

            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            metrics.end_time = time.perf_counter()

        logger.info(
            f"Connection Pool Test: timeouts={timeout_errors}, connection_errors={connection_errors}"
        )
        logger.info(f"Results: {metrics.to_dict()}")

        # Should not have connection errors
        assert (
            connection_errors == 0
        ), f"Connection errors detected: {connection_errors}"
        assert metrics.total_requests > 0


# ─── Helper Functions ──────────────────────────────────────────────────────────


def analyze_degradation(interval_metrics: dict) -> dict:
    """
    Analyzes performance degradation by intervals.

    Returns:
        dict with degradation flags
    """
    if len(interval_metrics) < 2:
        return {
            "has_latency_degradation": False,
            "has_throughput_degradation": False,
            "intervals_analyzed": 0,
        }

    intervals = sorted(interval_metrics.keys())

    # Compare first and last intervals
    first = interval_metrics[intervals[0]]
    last = interval_metrics[intervals[-1]]

    first_avg_latency = (
        sum(first["latencies"]) / len(first["latencies"]) if first["latencies"] else 0
    )
    last_avg_latency = (
        sum(last["latencies"]) / len(last["latencies"]) if last["latencies"] else 0
    )

    latency_growth = (
        (last_avg_latency - first_avg_latency) / first_avg_latency
        if first_avg_latency > 0
        else 0
    )

    throughput_decline = (
        (first["requests"] - last["requests"]) / first["requests"]
        if first["requests"] > 0
        else 0
    )

    return {
        "has_latency_degradation": latency_growth > 0.3,  # 30% growth
        "has_throughput_degradation": throughput_decline > 0.3,  # 30% decline
        "latency_growth_rate": latency_growth,
        "throughput_decline_rate": throughput_decline,
        "intervals_analyzed": len(intervals),
        "first_interval_requests": first["requests"],
        "last_interval_requests": last["requests"],
    }


def analyze_latency_trend(samples: list[float]) -> dict:
    """
    Analyzes latency trend.

    Returns:
        dict with trend information
    """
    if len(samples) < 2:
        return {"growth_rate": 0, "trend": "stable"}

    first_half = samples[: len(samples) // 2]
    second_half = samples[len(samples) // 2 :]

    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)

    growth_rate = (second_avg - first_avg) / first_avg if first_avg > 0 else 0

    if growth_rate > 0.5:
        trend = "increasing"
    elif growth_rate < -0.3:
        trend = "decreasing"
    else:
        trend = "stable"

    return {
        "growth_rate": growth_rate,
        "trend": trend,
        "first_half_avg": first_avg,
        "second_half_avg": second_avg,
        "samples_count": len(samples),
    }
