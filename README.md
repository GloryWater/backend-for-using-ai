# 🤖 AdManager - AI-Powered Ad Text Editor

[![alt text](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![alt text](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![alt text](https://img.shields.io/badge/Aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)](https://docs.docker.com/compose/)
[![alt text](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![alt text](https://img.shields.io/badge/Vector_DB-Qdrant-D32F2F?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![alt text](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![alt text](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Сервис автоматического редактирования рекламных объявлений с использованием LLM (Large Language Models) и RAG (Retrieval-Augmented Generation). Включает Telegram-бота для управления лицензиями и приёма платежей.

## 📋 Содержание

- [Возможности](#-возможности)
- [Архитектура](#-архитектура)
- [Технологический стек](#-технологический-стек)
- [Быстрый старт](#-быстрый-старт)
- [Конфигурация](#-конфигурация)
- [API Endpoints](#-api-endpoints)
- [Структура проекта](#-структура-проекта)
- [Разработка](#-разработка)
- [Платежные системы](#-платежные-системы)

## ✨ Возможности

### Основной функционал
- 🤖 **AI-редактирование текстов** с использованием LLM (совместимость с OpenAI API)
- 🔍 **RAG-система** для контекстного улучшения качества редактирования
- 🎯 **Векторный поиск** похожих примеров через Qdrant
- 🔐 **Система лицензирования** с привязкой к HWID
- 📱 **Telegram-бот** для управления подписками

### Монетизация
- ⭐ **Telegram Stars** - встроенная оплата
- 💎 **Криптовалюта** - через CryptoCloud/Cryptomus
- 💳 **Банковские карты** - через Tribute
- 🎁 **Пробный период** - 7 дней бесплатно

### Безопасность
- 🔒 XOR-шифрование скриптов
- 🔑 HMAC-верификация вебхуков
- 🖥️ Привязка к устройству (HWID)
- ⏰ Управление сроком действия лицензий

## 🏗️ Архитектура

```
┌─────────────────┐
│  Telegram Bot   │
│   (aiogram)     │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────┐
│          FastAPI Backend            │
│  ┌─────────────────────────────┐   │
│  │      AI Service (LLM)       │   │
│  │   ┌─────────────────────┐   │   │
│  │   │   Vector Store      │   │   │
│  │   │    (Qdrant)         │   │   │
│  │   └─────────────────────┘   │   │
│  └─────────────────────────────┘   │
└──────────────┬──────────────────────┘
               │
               ↓
    ┌──────────────────────┐
    │   PostgreSQL DB      │
    │  (Users, Licenses)   │
    └──────────────────────┘
```

## 🛠️ Технологический стек

### Backend
- **FastAPI** - современный async веб-фреймворк
- **SQLAlchemy 2.0** - ORM с поддержкой async/await
- **Alembic** - миграции базы данных
- **Pydantic** - валидация данных

### AI/ML
- **OpenAI API** - LLM для генерации текстов
- **Sentence Transformers** - эмбеддинги для векторного поиска
- **Qdrant** - векторная база данных
- **LangChain Community** - инструменты для RAG

### Infrastructure
- **PostgreSQL 15** - основная БД
- **Docker Compose** - оркестрация сервисов
- **Uvicorn** - ASGI сервер
- **aiogram 3** - Telegram Bot framework

### Payments
- **Telegram Stars** - встроенные платежи
- **CryptoCloud** - криптовалютные платежи
- **Tribute** - платежи картами

## 🚀 Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)
- Telegram Bot Token
- API ключи для LLM (OpenAI-совместимый API)

### Установка

1. **Клонируйте репозиторий**
```bash
git clone https://github.com/yourusername/admanager.git
cd admanager
```

2. **Создайте файл .env**
```bash
cp .env.example .env
```

3. **Настройте переменные окружения** (см. [Конфигурация](#-конфигурация))

4. **Запустите сервисы**
```bash
docker-compose up -d
```

5. **Проверьте статус**
```bash
docker-compose ps
```

Сервисы будут доступны:
- API: http://localhost:8000
- Qdrant UI: http://localhost:6333/dashboard
- PostgreSQL: localhost:7432

### Первый запуск

1. **Примените миграции БД**
```bash
docker-compose exec backend alembic upgrade head
```

2. **Загрузите примеры для RAG**
Поместите файл `src/AI/data.jsonl` с обучающими примерами

3. **Добавьте правила редактирования**
Создайте `src/AI/rules.xml` с правилами для LLM

4. **Загрузите Lua-скрипт**
Поместите `protected/scriptV2.lua` для раздачи клиентам

## ⚙️ Конфигурация

### Основные переменные (.env)

```bash
# Database
DB_USER=postgres
DB_PASS=your_secure_password
DB_NAME=admanager
DB_HOST=db
DB_PORT=5432

# LLM Configuration
LLM_API_KEY=your_llm_api_key
LLM_BASE_URL=https://api.openai.com/v1  # или другой совместимый API
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=200

# Telegram Bot
BOT_TOKEN=your_telegram_bot_token

# Payment Systems
CRYPTOCLOUD_API_KEY=your_cryptocloud_key
CRYPTOCLOUD_SHOP_ID=your_shop_id
CRYPTOCLOUD_SECRET=your_secret

TRIBUTE_API_KEY=your_tribute_key

# ML/Vector DB
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=examples_collection
ML_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
SIMILARITY_THRESHOLD=0.5
TOP_K_EXAMPLES=10

# Files
RULES_FILE=src/AI/rules.xml
EXAMPLES_FILE=src/AI/data.jsonl
SCRIPT_PATH=protected/scriptV2.lua
LOADER_VERSION_FILE=loader_version.json
```

### Формат обучающих данных (data.jsonl)

```jsonl
{"messages": [{"role": "user", "content": "исходный текст объявления"}, {"role": "model", "content": "отредактированный текст"}]}
{"messages": [{"role": "user", "content": "еще один пример"}, {"role": "model", "content": "результат редактирования"}]}
```

### Формат правил (rules.xml)

```xml
<rules>
  <rule>Убирай эмодзи из текста</rule>
  <rule>Исправляй орфографические ошибки</rule>
  <rule>Сокращай текст до 100 символов</rule>
  <!-- другие правила -->
</rules>
```

## 📡 API Endpoints

### Authentication

```http
POST /auth
Content-Type: application/json

{
  "key": "license_key",
  "hwid": "hardware_id"
}
```

**Response:**
```json
{
  "status": "success",
  "script_bytes": "base64_encoded_encrypted_script"
}
```

### AI Text Editing

```http
POST /edit
Content-Type: application/json

{
  "key": "license_key",
  "hwid": "hardware_id",
  "text": "текст для редактирования"
}
```

**Response:**
```json
{
  "result": "отредактированный текст"
}
```

### Webhooks

**CryptoCloud Postback:**
```http
POST /callback
```

**Tribute Webhook:**
```http
POST /webhook/tribute
Header: trbt-signature: hmac_signature
```

### Version Check

```http
GET /loader/version
```

**Response:**
```json
{
  "version": "1.0.0",
  "url": "https://example.com/loader.lua"
}
```

## 📁 Структура проекта

```
admanager/
├── alembic/                  # Миграции БД
│   ├── env.py
│   └── versions/
├── src/
│   ├── AI/                   # AI конфигурация
│   │   ├── rules.xml         # Правила редактирования
│   │   └── data.jsonl        # Обучающие примеры
│   ├── bot/                  # Telegram бот
│   │   ├── bot.py            # Основная логика
│   │   └── keyboards.py      # Клавиатуры
│   ├── database/             # База данных
│   │   ├── models.py         # SQLAlchemy модели
│   │   ├── crud.py           # CRUD операции
│   │   └── db.py             # Подключение к БД
│   ├── routes/               # API маршруты
│   │   ├── ai.py             # AI endpoints
│   │   ├── auth.py           # Авторизация
│   │   └── payments.py       # Платежи
│   ├── services/             # Бизнес-логика
│   │   ├── ai_service.py     # AI сервис
│   │   ├── vector_store.py   # Qdrant интеграция
│   │   ├── notification_service.py
│   │   └── cryptocloud.py    # Платежный API
│   ├── utils/                # Утилиты
│   │   ├── crypto.py         # Шифрование
│   │   └── text.py           # Обработка текста
│   ├── config.py             # Конфигурация
│   ├── dependencies.py       # FastAPI dependencies
│   ├── schemas.py            # Pydantic схемы
│   └── main.py               # Точка входа
├── protected/                # Защищенные файлы
│   └── scriptV2.lua          # Lua скрипт для клиентов
├── static/                   # Статические файлы
│   └── loader.lua            # Загрузчик
├── docker-compose.yaml       # Docker конфигурация
├── Dockerfile                # Docker образ
├── pyproject.toml            # Зависимости Python
└── README.md                 # Документация
```

## 👨‍💻 Разработка

### Локальная разработка

1. **Создайте виртуальное окружение**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

2. **Установите зависимости**
```bash
pip install -e .
```

3. **Запустите сервисы в фоне**
```bash
docker-compose up -d db qdrant
```

4. **Запустите backend локально**
```bash
uvicorn src.main:app --reload --port 8000
```

5. **Запустите бота отдельно**
```bash
python -m src.bot.bot
```

### Создание миграций

```bash
# Автогенерация миграции
alembic revision --autogenerate -m "описание изменений"

# Применение миграций
alembic upgrade head

# Откат миграции
alembic downgrade -1
```

### Тестирование векторного поиска

```python
from src.services.vector_store import VectorStore
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
store = VectorStore(
    qdrant_url="http://localhost:6333",
    collection_name="examples_collection",
    model=model
)

# Инициализация и поиск
await store.initialize("src/AI/data.jsonl")
results = await store.find_similar("ваш запрос")
print(results)
```

## 💳 Платежные системы

### Telegram Stars

Встроенная система оплаты Telegram. Настройка:
1. Создайте бота через [@BotFather](https://t.me/botfather)
2. Активируйте Telegram Stars
3. Укажите BOT_TOKEN в `.env`

### CryptoCloud / Cryptomus

Прием криптовалютных платежей:
1. Зарегистрируйтесь на [CryptoCloud](https://cryptocloud.plus/)
2. Получите API ключи в личном кабинете
3. Настройте вебхук на `https://yourdomain.com/callback`
4. Добавьте ключи в `.env`

### Tribute

Прием платежей картами:
1. Создайте продукт в [Tribute](https://tribute.app/)
2. Настройте вебхук на `https://yourdomain.com/webhook/tribute`
3. Добавьте TRIBUTE_API_KEY в `.env`
4. Используйте HMAC-подпись для верификации

## 🔒 Безопасность

### HWID Lock
Лицензия привязывается к первому устройству при активации. Сброс возможен через Telegram бота.

### XOR Encryption
Lua-скрипты шифруются XOR-алгоритмом с использованием лицензионного ключа.

### Webhook Verification
Все вебхуки проверяются через HMAC-подписи для предотвращения подделки.

### Database Security
- Используйте сильные пароли
- Ограничьте доступ к PostgreSQL (127.0.0.1)
- Регулярно создавайте бэкапы

## 📊 Мониторинг

### Логи

```bash
# Все сервисы
docker-compose logs -f

# Только backend
docker-compose logs -f backend

# Только бот
docker-compose logs -f bot
```

### Метрики Qdrant

Доступны в UI: http://localhost:6333/dashboard

### Проверка здоровья

```bash
# API
curl http://localhost:8000/docs

# База данных
docker-compose exec db psql -U postgres -d admanager -c "SELECT COUNT(*) FROM users;"
```

## 🤝 Участие в разработке

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request


## ⚖️ License & Legal

**© 2026 Yauheni Sytsevich. All Rights Reserved.**

This project is **PROPRIETARY SOFTWARE**.
Unauthorized copying, modification, distribution, or reverse engineering of this software, via any medium, is strictly prohibited.