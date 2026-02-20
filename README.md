# 🤖 AdManager — AI-сервис для редактирования рекламных объявлений

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI 0.110](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Aiogram 3.x](https://img.shields.io/badge/Aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![PostgreSQL 15](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Qdrant](https://img.shields.io/badge/Vector_DB-Qdrant-D32F2F?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![CI](https://github.com/GloryWater/backend-for-using-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/GloryWater/backend-for-using-ai/actions/workflows/ci.yml)

Сервис автоматического редактирования рекламных объявлений с использованием LLM и RAG-системы. Включает Telegram-бота для управления подписками, приёма платежей и системы лицензирования с привязкой к HWID.

---

## 📋 Содержание

- [Возможности](#-возможности)
- [Архитектура](#-архитектура)
- [Технологический стек](#-технологический-стек)
- [Быстрый старт](#-быстрый-старт)
- [Конфигурация](#-конфигурация)
- [API Reference](#-api-reference)
- [Структура проекта](#-структура-проекта)
- [Разработка](#-разработка)
- [Платежные системы](#-платежные-системы)
- [Безопасность](#-безопасность)
- [Лицензия](#-лицензия)

---

## ✨ Возможности

### Основной функционал
- 🤖 **AI-редактирование текстов** — использование LLM (OpenAI-совместимый API) для улучшения рекламных объявлений
- 🔍 **RAG-система** — Retrieval-Augmented Generation для контекстного редактирования на основе обучающих примеров
- 🎯 **Векторный поиск** — семантический поиск похожих примеров через Qdrant (Sentence Transformers)
- 🔐 **Система лицензирования** — генерация и валидация лицензий с привязкой к HWID
- 📱 **Telegram-бот** — управление подписками, пробными периодами и оплатами

### Монетизация
- ⭐ **Telegram Stars** — встроенная оплата через Telegram
- 💎 **Криптовалюта** — CryptoCloud/Cryptomus для приёма криптовалютных платежей
- 💳 **Банковские карты** — Tribute для обработки карточных платежей
- 🎁 **Пробный период** — 7 дней бесплатного использования

### Безопасность
- 🔒 **XOR-шифрование** — защита Lua-скриптов
- 🔑 **HMAC-верификация** — проверка подписи вебхуков
- 🖥️ **HWID Lock** — привязка лицензии к устройству
- ⏰ **Срок действия** — управление активацией лицензий

---

## 🏗️ Архитектура

```
┌─────────────────┐
│  Telegram Bot   │
│   (aiogram 3)   │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│          FastAPI Backend                │
│  ┌───────────────────────────────────┐  │
│  │       AIService (LLM + RAG)       │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │   VectorStore (Qdrant)      │  │  │
│  │  │   Sentence Transformers     │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │   Payment Services                │  │
│  │   • CryptoCloud                   │  │
│  │   • Tribute                       │  │
│  │   • Telegram Stars                │  │
│  └───────────────────────────────────┘  │
└──────────────────┬──────────────────────┘
                   │
                   ↓
    ┌──────────────────────────┐
    │   PostgreSQL 15          │
    │  • Users                 │
    │  • Licenses              │
    │  • Payments              │
    └──────────────────────────┘
```

---

## 🛠️ Технологический стек

### Backend
| Технология | Версия | Назначение |
|------------|--------|------------|
| **FastAPI** | 0.110+ | Async веб-фреймворк |
| **SQLAlchemy** | 2.0+ | ORM с async/await |
| **Alembic** | 1.18+ | Миграции БД |
| **Pydantic** | 2.8+ | Валидация данных |
| **AsyncPG** | 0.29+ | PostgreSQL драйвер |

### AI/ML
| Технология | Версия | Назначение |
|------------|--------|------------|
| **OpenAI API** | 1.40+ | LLM для генерации |
| **Sentence Transformers** | 3.0+ | Эмбеддинги |
| **Qdrant** | 1.12+ | Векторная БД |
| **LangChain Community** | 0.3+ | RAG инструменты |
| **NumPy** | <2.0 | Математические операции |

### Infrastructure
| Технология | Версия | Назначение |
|------------|--------|------------|
| **PostgreSQL** | 15 | Основная БД |
| **Docker Compose** | — | Оркестрация |
| **Uvicorn** | 0.30+ | ASGI сервер |
| **aiogram** | 3.10+ | Telegram Bot |

### DevOps & Tools
| Технология | Версия | Назначение |
|------------|--------|------------|
| **GitHub Actions** | — | CI/CD |
| **Ruff** | 0.15+ | Линтинг |
| **Mypy** | 1.19+ | Статическая типизация |
| **Pytest** | 9.0+ | Тестирование |
| **Pre-commit** | 4.5+ | Хуки Git |

---

## 🚀 Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)
- Telegram Bot Token (от [@BotFather](https://t.me/botfather))
- API ключ для LLM (OpenAI-совместимый)

### Установка

1. **Клонируйте репозиторий**
```bash
git clone https://github.com/GloryWater/backend-for-using-ai.git
cd backend-for-using-ai
```

2. **Создайте файл окружения**
```bash
cp .env.example .env  # или создайте .env вручную
```

3. **Настройте переменные окружения** (см. [Конфигурация](#-конфигурация))

4. **Запустите все сервисы**
```bash
docker-compose up -d
```

5. **Проверьте статус контейнеров**
```bash
docker-compose ps
```

6. **Примените миграции БД**
```bash
docker-compose exec backend alembic upgrade head
```

### Проверка работы

Сервисы доступны по адресам:
- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **PostgreSQL**: localhost:5432 (только изнутри сети)

---

## ⚙️ Конфигурация

### Основные переменные окружения

Создайте файл `.env` в корне проекта:

```bash
# ─── Database ──────────────────────────────────────────
DB_USER=postgres
DB_PASS=your_secure_password_here
DB_NAME=admanager
DB_HOST=db
DB_PORT=5432

# ─── LLM Configuration ─────────────────────────────────
LLM_API_KEY=your_llm_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=200

# ─── Telegram Bot ──────────────────────────────────────
BOT_TOKEN=your_telegram_bot_token_here

# ─── Payment Systems ───────────────────────────────────
CRYPTOCLOUD_API_KEY=
CRYPTOCLOUD_SHOP_ID=
CRYPTOCLOUD_SECRET=

TRIBUTE_API_KEY=your_tribute_api_key

# ─── ML / Vector DB ────────────────────────────────────
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=examples_collection
ML_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
SIMILARITY_THRESHOLD=0.5
TOP_K_EXAMPLES=10

# ─── Files & Paths ─────────────────────────────────────
RULES_FILE=src/AI/rules.xml
EXAMPLES_FILE=src/AI/data.jsonl
SCRIPT_PATH=protected/scriptV2.lua
LOADER_VERSION_FILE=loader_version.json
```

### Формат обучающих данных (`data.jsonl`)

Каждая строка — JSON-объект с диалогом для обучения:

```jsonl
{"messages": [{"role": "user", "content": "реклама ломбарда 329 330"}, {"role": "model", "content": "Работают ломбарды на 329 и 330 авеню. Лучшие цены в штате. Отправил:"}]}
{"messages": [{"role": "user", "content": "куплю ламборгини хуракан 2022"}, {"role": "model", "content": "Куплю а/м марки \"Ламборгини Хуракан 2022\". Бюджет: Свободный."}]}
```

### Формат правил редактирования (`rules.xml`)

```xml
<rules>
  <rule>Убирай эмодзи из текста</rule>
  <rule>Исправляй орфографические ошибки</rule>
  <rule>Сокращай текст до 100 символов</rule>
  <rule>Стандартизируй форматы цен (650кк → 650 млн)</rule>
  <rule>Используй аббревиатуры: а/м (автомобиль), о/п (одежда/пошив), р/с (ресурс/сертификат)</rule>
</rules>
```

---

## 📡 API Reference

### Authentication

**POST** `/auth`

Аутентификация лицензии и получение зашифрованного скрипта.

```http
POST /auth
Content-Type: application/json

{
  "key": "license_key_123",
  "hwid": "hardware_id_abc"
}
```

**Response 200:**
```json
{
  "status": "success",
  "script_bytes": "base64_encoded_encrypted_script"
}
```

**Response 403:**
```json
{
  "status": "error",
  "message": "Invalid license"
}
```

---

### AI Text Editing

**POST** `/edit`

Редактирование текста объявления через AI.

```http
POST /edit
Content-Type: application/json

{
  "key": "license_key_123",
  "hwid": "hardware_id_abc",
  "text": "продам лавку чубрика 650кк"
}
```

**Response 200:**
```json
{
  "result": "Продам а/с \"Лавка Чубрика\". Цена: 650 млн."
}
```

---

### Loader Version

**GET** `/loader/version`

Проверка версии загрузчика.

```http
GET /loader/version
```

**Response 200:**
```json
{
  "version": "0.1",
  "url": "https://glorysyntax.live/static/loader.lua"
}
```

---

### Payment Webhooks

**POST** `/callback` — CryptoCloud postback  
**POST** `/webhook/tribute` — Tribute webhook (требует HMAC-подпись в заголовке `trbt-signature`)

---

## 📁 Структура проекта

```
admanager/
├── alembic/                      # Миграции базы данных
│   ├── env.py
│   └── versions/                 # Файлы миграций
│
├── src/
│   ├── AI/                       # AI конфигурация
│   │   ├── rules.xml             # Правила редактирования
│   │   └── data.jsonl            # Обучающие примеры (6500+ строк)
│   │
│   ├── bot/                      # Telegram бот
│   │   ├── bot.py                # Основная логика
│   │   └── keyboards.py          # Inline/reply клавиатуры
│   │
│   ├── database/                 # Работа с БД
│   │   ├── models.py             # SQLAlchemy модели (User, License, Payment)
│   │   ├── crud.py               # CRUD операции
│   │   └── db.py                 # Подключение к PostgreSQL
│   │
│   ├── rag/                      # RAG компоненты
│   │
│   ├── routes/                   # API endpoints
│   │   ├── ai.py                 # /edit — AI редактирование
│   │   ├── auth.py               # /auth, /loader/version
│   │   └── payments.py           # Платежные вебхуки
│   │
│   ├── services/                 # Бизнес-логика
│   │   ├── ai_service.py         # AIService (LLM + RAG)
│   │   ├── vector_store.py       # Qdrant интеграция
│   │   ├── notification_service.py # Уведомления через бота
│   │   └── cryptocloud.py        # CryptoCloud API
│   │
│   ├── utils/                    # Утилиты
│   │   ├── crypto.py             # XOR шифрование, HMAC
│   │   └── text.py               # Очистка текста
│   │
│   ├── config.py                 # Pydantic Settings
│   ├── dependencies.py           # FastAPI Depends
│   ├── schemas.py                # Pydantic модели
│   └── main.py                   # Точка входа (lifespan, роутеры)
│
├── protected/                    # Защищённые файлы
│   └── scriptV2.lua              # Lua скрипт для клиентов
│
├── static/                       # Статические файлы
│   └── loader.lua                # Загрузчик
│
├── tests/                        # Тесты (pytest)
│
├── .github/
│   └── workflows/
│       └── ci.yml                # CI/CD (тесты + build & push)
│
├── docker-compose.yaml           # Оркестрация сервисов
├── Dockerfile                    # Образ приложения
├── pyproject.toml                # Зависимости Python (uv)
├── .pre-commit-config.yaml       # Pre-commit хуки (Ruff, Mypy)
├── .python-version               # Версия Python (3.11)
├── alembic.ini                   # Настройки Alembic
└── README.md                     # Документация
```

---

## 👨‍💻 Разработка

### Локальная разработка

1. **Установите uv** (менеджер пакетов)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Склонируйте и настройте окружение**
```bash
git clone https://github.com/GloryWater/backend-for-using-ai.git
cd backend-for-using-ai
uv sync
```

3. **Запустите зависимости (Docker)**
```bash
docker-compose up -d db qdrant
```

4. **Запустите backend локально**
```bash
uvicorn src.main:app --reload --port 8000
```

5. **Запустите бота (отдельно)**
```bash
python -m src.bot.bot
```

### Pre-commit хуки

Проект использует pre-commit для автоматического линтинга:

```bash
# Установка хуков
pre-commit install

# Запуск на всех файлах
pre-commit run --all-files
```

Хуки включают:
- **Ruff** — линтинг и форматирование
- **Mypy** — проверка типов

### Создание миграций

```bash
# Автогенерация миграции
alembic revision --autogenerate -m "описание изменений"

# Применение миграций
alembic upgrade head

# Откат на одну миграцию
alembic downgrade -1
```

### Тестирование

Проект использует **pytest** для тестирования. Тесты разделены на две категории:

#### Быстрые тесты (Unit/Integration)

Запускаются **по умолчанию** без необходимости в запущенном сервере:

```bash
# Все быстрые тесты
pytest

# С подробным выводом
pytest -v

# С покрытием кода
pytest --cov=src

# Конкретный файл тестов
pytest tests/test_api.py -v
pytest tests/test_crud.py -v
pytest tests/test_crypto.py -v
pytest tests/test_rate_limit.py -v
```

#### Load/Stress тесты

Требуют **запущенного сервера** и флага `--load`:

```bash
# Быстрые load тесты (10-30 сек каждый)
pytest tests/load/ -v --load

# Полные load тесты (60-300 сек каждый)
pytest tests/load/ -v --load --full-mode

# Конкретный тип тестов
pytest tests/load/ -v --load -m stress
pytest tests/load/ -v --load -m soak
pytest tests/load/ -v --load -m spike
pytest tests/load/ -v --load -m chaos

# С кастомными параметрами
pytest tests/load/ -v --load --concurrent-users=50 --test-duration=60

# С генерацией HTML отчёта
pytest tests/load/ -v --load --generate-report
```

#### Конфигурация load тестов

| Параметр | По умолчанию | Полный режим | Описание |
|----------|--------------|--------------|----------|
| `--concurrent-users` | 5 | 10 | Количество одновременных пользователей |
| `--test-duration` | 10 сек | 60 сек | Длительность теста |
| `--spike-users` | 20 | 100 | Пользователей для spike тестов |
| `--soak-duration` | 30 сек | 300 сек | Длительность soak тестов |
| `--timeout-seconds` | 10 сек | 30 сек | Таймаут запроса |

#### Маркеры тестов

- `load` — нагрузочные тесты
- `stress` — стресс-тесты (предельная нагрузка)
- `soak` — тесты стабильности (длительная работа)
- `spike` — тесты резких скачков нагрузки
- `chaos` — chaos engineering (сбои и отказы)

> **Важно:** Load тесты пропускаются по умолчанию. Используйте флаг `--load` для их запуска.

---

## 💳 Платежные системы

### Telegram Stars

Встроенная платёжная система Telegram:

1. Создайте бота через [@BotFather](https://t.me/botfather)
2. Активируйте Telegram Stars в настройках бота
3. Укажите `BOT_TOKEN` в `.env`

### CryptoCloud / Cryptomus

Приём криптовалютных платежей:

1. Зарегистрируйтесь на [CryptoCloud](https://cryptocloud.plus/)
2. Получите API ключи в личном кабинете
3. Настройте вебхук на `https://yourdomain.com/callback`
4. Добавьте в `.env`:
   ```bash
   CRYPTOCLOUD_API_KEY=your_key
   CRYPTOCLOUD_SHOP_ID=your_shop_id
   CRYPTOCLOUD_SECRET=your_secret
   ```

### Tribute

Приём платежей банковскими картами:

1. Создайте продукт в [Tribute](https://tribute.app/)
2. Настройте вебхук на `https://yourdomain.com/webhook/tribute`
3. Добавьте `TRIBUTE_API_KEY` в `.env`
4. Вебхуки проверяются через HMAC-подпись (заголовок `trbt-signature`)

---

## 🔒 Безопасность

### HWID Lock

Лицензия привязывается к первому устройству при активации. Изменение HWID требует сброса через Telegram-бот.

### XOR Encryption

Lua-скрипты шифруются XOR-алгоритмом с использованием лицензионного ключа перед отправкой клиенту.

### Webhook Verification

Все платёжные вебхуки проверяются через HMAC-SHA256 подписи для предотвращения подделки запросов.

### Database Security

Рекомендации:
- Используйте сложные пароли для БД
- Ограничьте доступ к PostgreSQL (только `127.0.0.1`)
- Регулярно создавайте бэкапы: `docker-compose exec db pg_dump -U postgres admanager > backup.sql`

---

## 📊 Мониторинг

### Логи

```bash
# Все сервисы
docker-compose logs -f

# Только backend
docker-compose logs -f backend

# Только бот
docker-compose logs -f bot

# Последние 100 строк
docker-compose logs --tail=100 backend
```

### Проверка здоровья

```bash
# API (Swagger UI)
curl http://localhost:8000/docs

# База данных
docker-compose exec db psql -U postgres -d admanager -c "SELECT COUNT(*) FROM users;"

# Qdrant
curl http://localhost:6333/api/collections
```

### Watchtower (автообновление)

В `docker-compose.yaml` настроен Watchtower для автоматического обновления контейнеров:
- Проверяет обновления каждые 30 секунд
- Использует GitHub Container Registry (GHCR)
- Автоматически удаляет старые образы

---

## 🤝 Вклад в проект

Этот проект является **проприетарным ПО**. Вклад извне не принимается.

Если вы обнаружили проблему или у вас есть предложение, свяжитесь с владельцем репозитория напрямую.

---

## ⚖️ Лицензия

**© 2026 Yauheni Sytsevich. Все права защищены.**

Данное программное обеспечение является **ПРОПРИЕТАРНЫМ**.  
Несанкционированное копирование, модификация, распространение или обратная разработка данного ПО, на любом носителе, строго запрещены.

---

## 📞 Контакты

- **GitHub**: [@GloryWater](https://github.com/GloryWater)

---

<div align="center">

**AdManager** — Умное редактирование рекламных объявлений с помощью AI

</div>
