"""
Базовая конфигурация и утилиты для load/stress тестов.

Использование:
    # Запуск load тестов
    pytest tests/load/ -v --load-mode

    # Запуск с кастомными параметрами
    pytest tests/load/ -v --concurrent-users=50 --test-duration=60

    # Запуск только stress тестов
    pytest tests/load/ -v -m stress

    # Генерация отчёта
    pytest tests/load/ -v --generate-report
"""

import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import aiohttp

# ─── Configuration ─────────────────────────────────────────────────────────────


class TestMode(Enum):
    """Режимы тестирования."""

    LOAD = "load"  # Обычная нагрузка
    STRESS = "stress"  # Предельная нагрузка
    SOAK = "soak"  # Длительная работа
    SPIKE = "spike"  # Резкие скачки
    CHAOS = "chaos"  # Хаос-инжиниринг


@dataclass
class LoadTestConfig:
    """Конфигурация load тестов."""

    # Базовые настройки
    base_url: str = "http://localhost:8000"
    timeout_seconds: int = 30

    # Параметры нагрузки
    concurrent_users: int = 10
    ramp_up_seconds: int = 5
    test_duration_seconds: int = 60

    # Режим теста
    mode: TestMode = TestMode.LOAD

    # Для spike тестов
    spike_users: int = 100
    spike_duration_seconds: int = 10

    # Для soak тестов
    soak_duration_seconds: int = 300  # 5 минут

    # Для chaos тестов
    chaos_probability: float = 0.1  # Вероятность сбоя

    # Отчётность
    generate_report: bool = True
    report_dir: str = "tests/load/reports"

    # Валидация лицензий для тестов
    test_license_key: str = "test_license_key_12345678"
    test_hwid: str = "test_hwid_12345"

    @classmethod
    def from_pytest_config(cls, request) -> "LoadTestConfig":
        """Создаёт конфигурацию из pytest параметров."""
        return cls(
            base_url=request.config.getoption("--base-url", default=cls.base_url),
            concurrent_users=request.config.getoption(
                "--concurrent-users", default=cls.concurrent_users
            ),
            ramp_up_seconds=request.config.getoption(
                "--ramp-up-seconds", default=cls.ramp_up_seconds
            ),
            test_duration_seconds=request.config.getoption(
                "--test-duration", default=cls.test_duration_seconds
            ),
            spike_users=request.config.getoption(
                "--spike-users", default=cls.spike_users
            ),
            soak_duration_seconds=request.config.getoption(
                "--soak-duration", default=cls.soak_duration_seconds
            ),
            mode=TestMode(request.config.getoption("--mode", default="load")),
            generate_report=request.config.getoption("--generate-report", default=True),
        )


@dataclass
class RequestResult:
    """Результат одного запроса."""

    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    timestamp: float
    error: Optional[str] = None
    request_size: int = 0
    response_size: int = 0


@dataclass
class LoadTestMetrics:
    """Агрегированные метрики теста."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    latencies: list[float] = field(default_factory=list)
    errors: dict[str, int] = field(default_factory=dict)

    start_time: float = 0
    end_time: float = 0

    # Расчётные метрики
    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time

    @property
    def requests_per_second(self) -> float:
        if self.duration_seconds <= 0:
            return 0
        return self.total_requests / self.duration_seconds

    @property
    def success_rate(self) -> float:
        if self.total_requests <= 0:
            return 0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def error_rate(self) -> float:
        if self.total_requests <= 0:
            return 0
        return (self.failed_requests / self.total_requests) * 100

    @property
    def latency_p50(self) -> float:
        if not self.latencies:
            return 0
        return statistics.median(self.latencies)

    @property
    def latency_p95(self) -> float:
        if not self.latencies:
            return 0
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]

    @property
    def latency_p99(self) -> float:
        if not self.latencies:
            return 0
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]

    @property
    def latency_mean(self) -> float:
        if not self.latencies:
            return 0
        return statistics.mean(self.latencies)

    @property
    def latency_stdev(self) -> float:
        if len(self.latencies) < 2:
            return 0
        return statistics.stdev(self.latencies)

    def to_dict(self) -> dict:
        """Конвертирует метрики в словарь."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.success_rate, 2),
            "error_rate": round(self.error_rate, 2),
            "requests_per_second": round(self.requests_per_second, 2),
            "duration_seconds": round(self.duration_seconds, 2),
            "latency_p50_ms": round(self.latency_p50, 2),
            "latency_p95_ms": round(self.latency_p95, 2),
            "latency_p99_ms": round(self.latency_p99, 2),
            "latency_mean_ms": round(self.latency_mean, 2),
            "latency_stdev_ms": round(self.latency_stdev, 2),
            "errors": self.errors,
        }


class LoadTestSession:
    """Сессия для load тестирования."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.metrics = LoadTestMetrics()
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self.logger = logging.getLogger(__name__)

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        connector = aiohttp.TCPConnector(
            limit=self.config.concurrent_users * 2,
            limit_per_host=self.config.concurrent_users,
        )
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": "AdManager-LoadTest/1.0"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> RequestResult:
        """Выполняет HTTP запрос и записывает метрики."""
        url = f"{self.config.base_url}{endpoint}"
        start_time = time.perf_counter()
        timestamp = time.time()

        request_size = len(json.dumps(json_data)) if json_data else 0
        error: Optional[str] = None
        status_code = 0
        response_size = 0

        try:
            # self.session гарантированно не None в контексте with
            assert self.session is not None, "Session not initialized"
            async with self.session.request(
                method,
                url,
                json=json_data,
                headers=headers,
            ) as response:
                status_code = response.status
                content = await response.read()
                response_size = len(content)

        except asyncio.TimeoutError:
            error = f"Timeout after {self.config.timeout_seconds}s"
            status_code = 504
        except aiohttp.ClientError as e:
            error = str(e)
            status_code = 599
        except Exception as e:
            error = str(e)
            status_code = 599

        latency_ms = (time.perf_counter() - start_time) * 1000

        result = RequestResult(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
            timestamp=timestamp,
            error=error,
            request_size=request_size,
            response_size=response_size,
        )

        # Обновляем метрики
        await self._record_result(result)

        return result

    async def _record_result(self, result: RequestResult):
        """Записывает результат в метрики."""
        async with self._lock:
            self.metrics.total_requests += 1

            if result.status_code < 400:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
                error_key = f"{result.status_code}"
                if result.error:
                    error_key = f"{result.status_code}_{result.error[:50]}"
                self.metrics.errors[error_key] = (
                    self.metrics.errors.get(error_key, 0) + 1
                )

            self.metrics.latencies.append(result.latency_ms)

    def stop(self):
        """Останавливает тест."""
        self._stop_event.set()

    @property
    def is_running(self) -> bool:
        return not self._stop_event.is_set()


# ─── Pytest Configuration ──────────────────────────────────────────────────────


def pytest_addoption(parser):
    """Добавляет CLI опции для pytest."""
    parser.addoption(
        "--base-url",
        action="store",
        default="http://localhost:8000",
        help="Base URL of the service",
    )
    parser.addoption(
        "--concurrent-users",
        action="store",
        type=int,
        default=10,
        help="Number of concurrent users",
    )
    parser.addoption(
        "--ramp-up-seconds",
        action="store",
        type=int,
        default=5,
        help="Ramp-up time in seconds",
    )
    parser.addoption(
        "--test-duration",
        action="store",
        type=int,
        default=60,
        help="Test duration in seconds",
    )
    parser.addoption(
        "--mode",
        action="store",
        default="load",
        choices=["load", "stress", "soak", "spike", "chaos"],
        help="Test mode",
    )
    parser.addoption(
        "--spike-users",
        action="store",
        type=int,
        default=100,
        help="Number of users for spike test",
    )
    parser.addoption(
        "--soak-duration",
        action="store",
        type=int,
        default=300,
        help="Soak test duration in seconds",
    )
    parser.addoption(
        "--generate-report",
        action="store_true",
        default=True,
        help="Generate HTML report",
    )
    parser.addoption(
        "--load-mode",
        action="store_true",
        default=False,
        help="Enable load testing mode",
    )


def pytest_configure(config):
    """Настраивает pytest для load тестов."""
    config.addinivalue_line("markers", "load: mark test as load test")
    config.addinivalue_line("markers", "stress: mark test as stress test")
    config.addinivalue_line("markers", "soak: mark test as soak test")
    config.addinivalue_line("markers", "spike: mark test as spike test")
    config.addinivalue_line("markers", "chaos: mark test as chaos test")


# ─── Report Generation ─────────────────────────────────────────────────────────


def generate_report(metrics: LoadTestMetrics, config: LoadTestConfig) -> Path:
    """Генерирует HTML отчёт о тесте."""
    report_dir = Path(config.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"load_test_report_{timestamp}.html"

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Load Test Report - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
        .metric-label {{ color: #666; margin-top: 5px; }}
        .success {{ color: #28a745; }}
        .error {{ color: #dc3545; }}
        .warning {{ color: #ffc107; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #007bff; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .config {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .config-item {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e9ecef; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Load Test Report</h1>
        <p>Generated: {datetime.now(timezone.utc).isoformat()}</p>

        <h2>📈 Summary Metrics</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{metrics.total_requests}</div>
                <div class="metric-label">Total Requests</div>
            </div>
            <div class="metric">
                <div class="metric-value success">{metrics.success_rate:.1f}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value error">{metrics.error_rate:.1f}%</div>
                <div class="metric-label">Error Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics.requests_per_second:.1f}</div>
                <div class="metric-label">Requests/sec</div>
            </div>
        </div>

        <h2>⏱️ Latency Metrics</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{metrics.latency_mean:.1f}</div>
                <div class="metric-label">Mean (ms)</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics.latency_p50:.1f}</div>
                <div class="metric-label">P50 (ms)</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics.latency_p95:.1f}</div>
                <div class="metric-label">P95 (ms)</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics.latency_p99:.1f}</div>
                <div class="metric-label">P99 (ms)</div>
            </div>
        </div>

        <h2>❌ Errors</h2>
        <table>
            <tr><th>Error</th><th>Count</th><th>Percentage</th></tr>
            {"".join(f'<tr><td>{k}</td><td>{v}</td><td>{(v/metrics.total_requests)*100:.1f}%</td></tr>' for k, v in metrics.errors.items()) or '<tr><td colspan="3">No errors</td></tr>'}
        </table>

        <h2>⚙️ Test Configuration</h2>
        <div class="config">
            <div class="config-item"><span>Mode</span><span>{config.mode.value}</span></div>
            <div class="config-item"><span>Base URL</span><span>{config.base_url}</span></div>
            <div class="config-item"><span>Concurrent Users</span><span>{config.concurrent_users}</span></div>
            <div class="config-item"><span>Ramp-up Time</span><span>{config.ramp_up_seconds}s</span></div>
            <div class="config-item"><span>Test Duration</span><span>{config.test_duration_seconds}s</span></div>
            <div class="config-item"><span>Actual Duration</span><span>{metrics.duration_seconds:.1f}s</span></div>
        </div>
    </div>
</body>
</html>
"""

    report_file.write_text(html_content)
    return report_file


# ─── Helper Functions ──────────────────────────────────────────────────────────


async def ramp_up_users(
    session: LoadTestSession,
    target_users: int,
    ramp_up_seconds: int,
) -> list[asyncio.Task]:
    """Постепенно увеличивает количество пользователей."""
    tasks: list[asyncio.Task] = []
    delay = ramp_up_seconds / target_users if target_users > 0 else 0

    for i in range(target_users):
        if not session.is_running:
            break
        await asyncio.sleep(delay)
        # Задачи создаются в тестах

    return tasks


def calculate_sla_compliance(
    metrics: LoadTestMetrics,
    p95_target_ms: float = 1000,
    success_rate_target: float = 99.0,
) -> dict:
    """Проверяет соответствие SLA."""
    p95_compliant = metrics.latency_p95 <= p95_target_ms
    success_compliant = metrics.success_rate >= success_rate_target

    return {
        "overall_compliant": p95_compliant and success_compliant,
        "p95_latency_ms": metrics.latency_p95,
        "p95_target_ms": p95_target_ms,
        "p95_compliant": p95_compliant,
        "success_rate": metrics.success_rate,
        "success_rate_target": success_rate_target,
        "success_rate_compliant": success_compliant,
    }
