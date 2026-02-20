# Load Testing Suite для AdManager

Комплексный набор тестов износостойкости для проверки производительности и надёжности сервиса.

## 📋 Содержание

- [Типы тестов](#-типы-тестов)
- [Быстрый старт](#-быстрый-старт)
- [Конфигурация](#-конфигурация)
- [Запуск тестов](#-запуск-тестов)
- [Метрики и SLA](#-метрики-и-sla)
- [Отчётность](#-отчётность)
- [Интерпретация результатов](#-интерпретация-результатов)

---

## 📊 Типы тестов

| Тип | Описание | Длительность | Цель |
|-----|----------|--------------|------|
| **Load** | Нормальная нагрузка | 60 сек | Проверка работы под ожидаемой нагрузкой |
| **Stress** | Предельная нагрузка | 30 сек | Определение точки отказа |
| **Soak** | Длительная работа | 5-30 мин | Обнаружение утечек памяти, деградации |
| **Spike** | Резкие скачки | 70 сек | Проверка реакции на всплески трафика |
| **Chaos** | Сбои и отказы | 60-120 сек | Тестирование отказоустойчивости |

---

## 🚀 Быстрый старт

### Предварительные требования

```bash
# Установите зависимости
uv sync

# Запустите сервис
docker-compose up -d

# Убедитесь что сервис доступен
curl http://localhost:8000/health
```

### Запуск всех тестов

```bash
# Базовый запуск (10 пользователей, 60 секунд)
pytest tests/load/ -v --load-mode

# С кастомными параметрами
pytest tests/load/ -v --concurrent-users=50 --test-duration=120
```

---

## ⚙️ Конфигурация

### CLI параметры

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `--base-url` | `http://localhost:8000` | URL тестируемого сервиса |
| `--concurrent-users` | `10` | Количество одновременных пользователей |
| `--ramp-up-seconds` | `5` | Время постепенного увеличения нагрузки |
| `--test-duration` | `60` | Длительность теста в секундах |
| `--mode` | `load` | Режим теста (load/stress/soak/spike/chaos) |
| `--spike-users` | `100` | Количество пользователей для spike теста |
| `--soak-duration` | `300` | Длительность soak теста (5 минут) |
| `--generate-report` | `true` | Генерировать HTML отчёт |

### Примеры конфигурации

```bash
# Load тест с 50 пользователями
pytest tests/load/test_load.py -v --concurrent-users=50

# Stress тест
pytest tests/load/test_stress.py -v --mode=stress --concurrent-users=100

# Soak тест на 15 минут
pytest tests/load/test_soak.py -v --mode=soak --soak-duration=900

# Spike тест с 200 пользователями
pytest tests/load/test_spike.py -v --mode=spike --spike-users=200

# Chaos тест
pytest tests/load/test_chaos.py -v --mode=chaos
```

---

## 📈 Метрики и SLA

### Собираемые метрики

- **Total Requests** — общее количество запросов
- **Success Rate** — процент успешных запросов
- **Error Rate** — процент ошибок
- **Requests/sec** — пропускная способность
- **Latency P50** — медианное время ответа
- **Latency P95** — 95-й перцентиль времени ответа
- **Latency P99** — 99-й перцентиль времени ответа
- **Latency Mean** — среднее время ответа

### SLA требования

| Endpoint | P95 Latency | Success Rate | Throughput |
|----------|-------------|--------------|------------|
| `/health` | < 100ms | > 99.9% | > 100 req/s |
| `/auth` | < 500ms | > 99% | > 50 req/s |
| `/edit` | < 3000ms | > 95% | > 10 req/s |

### Проверка SLA

Тесты автоматически проверяют соответствие SLA:

```python
from tests.load.conftest import calculate_sla_compliance

sla = calculate_sla_compliance(
    metrics,
    p95_target_ms=500,
    success_rate_target=99.0
)

assert sla["overall_compliant"]  # True если все SLA выполнены
```

---

## 📊 Отчётность

### HTML отчёты

После каждого теста генерируется HTML отчёт в `tests/load/reports/`:

```
tests/load/reports/
└── load_test_report_20260220_143052.html
```

Отчёт включает:
- Сводные метрики
- Латенси перцентили
- Распределение ошибок
- Конфигурацию теста

### Пример отчёта

```html
📊 Load Test Report
Generated: 2026-02-20T14:30:52Z

📈 Summary Metrics
┌─────────────────┬─────────┐
│ Total Requests  │ 15420   │
│ Success Rate    │ 99.2%   │
│ Error Rate      │ 0.8%    │
│ Requests/sec    │ 257.0   │
└─────────────────┴─────────┘

⏱️ Latency Metrics
┌─────────────────┬─────────┐
│ Mean            │ 45.2ms  │
│ P50             │ 38.1ms  │
│ P95             │ 89.5ms  │
│ P99             │ 156.3ms │
└─────────────────┴─────────┘
```

---

## 🔍 Интерпретация результатов

### Load тесты

**✅ Хорошо:**
- Success rate > 99%
- P95 latency в пределах SLA
- Стабильный throughput

**❌ Проблемы:**
- Success rate < 95% — возможны проблемы с инфраструктурой
- P95 > 2x от target — нужна оптимизация
- Throughput ниже ожидаемого — проверьте bottleneck

### Stress тесты

**✅ Хорошо:**
- Система не падает полностью
- Graceful degradation (постепенное ухудшение)

**❌ Проблемы:**
- Cascading failures (каскадные отказы)
- Полная недоступность после превышения лимита

### Soak тесты

**✅ Хорошо:**
- Стабильная latency со временем
- Постоянный throughput
- Нет роста error rate

**❌ Проблемы:**
- Latency растёт > 30% за тест — возможна утечка памяти
- Throughput падает > 30% — истощение ресурсов
- Error rate увеличивается — накопление ошибок

### Spike тесты

**✅ Хорошо:**
- Быстрое восстановление (< 30 сек)
- Нет permanent damage после пика

**❌ Проблемы:**
- Долгое восстановление (> 60 сек)
- Ошибки продолжаются после нормализации нагрузки

### Chaos тесты

**✅ Хорошо:**
- Система выдерживает сбои
- Нет каскадных отказов
- Graceful degradation

**❌ Проблемы:**
- Единичный сбой вызывает полный отказ
- Нет recovery механизма

---

## 🧪 Сценарии использования

### Пре-продакшн проверка

```bash
# Полный цикл тестов перед релизом
pytest tests/load/test_load.py -v --concurrent-users=20
pytest tests/load/test_stress.py -v --concurrent-users=50
pytest tests/load/test_soak.py -v --soak-duration=600
```

### Поиск bottleneck

```bash
# Стресс-тест с постепенным увеличением нагрузки
for i in 10 20 50 100; do
    pytest tests/load/test_stress.py::TestStressAuthEndpoint \
        --concurrent-users=$i \
        --test-duration=30
done
```

### Мониторинг деградации

```bash
# Еженедельный soak тест
pytest tests/load/test_soak.py \
    --soak-duration=1800 \
    --generate-report
```

---

## 📁 Структура файлов

```
tests/load/
├── conftest.py           # Базовая конфигурация и утилиты
├── test_load.py          # Load тесты
├── test_stress.py        # Stress тесты
├── test_soak.py          # Soak тесты
├── test_spike.py         # Spike тесты
├── test_chaos.py         # Chaos тесты
└── reports/              # Сгенерированные отчёты
    └── load_test_report_*.html
```

---

## 🛠️ Расширение

### Добавление нового теста

```python
import pytest
from .conftest import LoadTestConfig, LoadTestSession, TestMetrics

@pytest.mark.load
async def test_custom_load(request):
    config = LoadTestConfig.from_pytest_config(request)
    metrics = LoadTestMetrics()

    async with LoadTestSession(config) as session:
        session.metrics = metrics
        metrics.start_time = time.perf_counter()

        async def worker():
            while session.is_running:
                await session.request("GET", "/your-endpoint")

        tasks = [asyncio.create_task(worker()) for _ in range(config.concurrent_users)]
        await asyncio.sleep(config.test_duration_seconds)
        session.stop()
        await asyncio.gather(*tasks, return_exceptions=True)

        metrics.end_time = time.perf_counter()

    assert metrics.success_rate > 95
```

### Кастомные метрики

```python
# В conftest.py добавьте в TestMetrics:
@property
def custom_metric(self) -> float:
    # Ваша логика расчёта
    return calculated_value
```

---

## ⚠️ Предостережения

1. **Не запускайте на production** без изоляции
2. **Резервируйте окружение** для тестов
3. **Мониторьте ресурсы** во время тестов
4. **Сохраняйте отчёты** для сравнения версий
5. **Настройте алерты** при нарушении SLA

---

## 📚 Дополнительные ресурсы

- [Locust.io](https://locust.io/) — альтернативный инструмент load тестирования
- [k6.io](https://k6.io/) — modern load testing tool
- [Chaos Engineering Principles](https://principlesofchaos.org/)
