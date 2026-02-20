"""
Расширенная конфигурация с валидацией и secrets management.
"""

import hashlib
import logging
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import (
    AnyHttpUrl,
    Field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Настройки базы данных."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    USER: str = Field(..., min_length=1, description="Имя пользователя БД")
    PASS: str = Field(
        ...,
        min_length=8,
        description="Пароль БД (минимум 8 символов)",
    )
    NAME: str = Field(..., min_length=1, description="Имя базы данных")
    HOST: str = Field(default="db", description="Хост БД")
    PORT: int = Field(default=5432, ge=1, le=65535, description="Порт БД")

    @property
    def url(self) -> str:
        """Возвращает DATABASE_URL."""
        return (
            f"postgresql+asyncpg://{self.USER}:{self.PASS}"
            f"@{self.HOST}:{self.PORT}/{self.NAME}"
        )

    @field_validator("PASS")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Проверяет сложность пароля."""
        if len(v) < 8:
            raise ValueError("Пароль должен быть не менее 8 символов")

        # Проверка на простые пароли
        weak_passwords = {"password", "postgres", "admin", "12345678"}
        if v.lower() in weak_passwords:
            raise ValueError("Слишком простой пароль")

        return v


class LLMSettings(BaseSettings):
    """Настройки LLM."""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_KEY: str = Field(..., min_length=10, description="API ключ LLM")
    BASE_URL: AnyHttpUrl = Field(
        ...,
        description="Базовый URL LLM API",
    )
    MODEL: str = Field(default="gpt-4o-mini", description="Модель LLM")
    TEMPERATURE: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Температура генерации",
    )
    MAX_TOKENS: int = Field(
        default=200,
        ge=1,
        le=4096,
        description="Максимум токенов в ответе",
    )


class TelegramSettings(BaseSettings):
    """Настройки Telegram."""

    model_config = SettingsConfigDict(
        env_prefix="BOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    TOKEN: str = Field(..., min_length=40, description="Токен Telegram бота")

    @field_validator("TOKEN")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        """Проверяет формат токена бота."""
        if ":" not in v:
            raise ValueError("Неверный формат токена бота")

        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Неверный формат токена бота")

        if not parts[0].isdigit():
            raise ValueError("Неверный формат токена бота (ID)")

        return v


class CryptoCloudSettings(BaseSettings):
    """Настройки CryptoCloud."""

    model_config = SettingsConfigDict(
        env_prefix="CRYPTOCLOUD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_KEY: str = Field(default="", description="API ключ CryptoCloud")
    SHOP_ID: str = Field(default="", description="ID магазина")
    SECRET: str = Field(default="", description="Секретный ключ")


class TributeSettings(BaseSettings):
    """Настройки Tribute."""

    model_config = SettingsConfigDict(
        env_prefix="TRIBUTE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_KEY: str = Field(..., min_length=1, description="API ключ Tribute")


class MLSettings(BaseSettings):
    """Настройки ML/Vector DB."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    RULES_FILE: str = Field(
        default="src/AI/rules.xml",
        description="Путь к файлу правил",
    )
    EXAMPLES_FILE: str = Field(
        default="src/AI/data.jsonl",
        description="Путь к файлу примеров",
    )
    ML_MODEL_NAME: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        description="Модель для эмбеддингов",
    )
    SIMILARITY_THRESHOLD: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Порог схожести",
    )
    TOP_K_EXAMPLES: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Количество примеров",
    )
    QDRANT_URL: str = Field(
        default="http://qdrant:6333",
        description="URL Qdrant",
    )
    QDRANT_COLLECTION: str = Field(
        default="examples_collection",
        description="Коллекция Qdrant",
    )


class AuthSettings(BaseSettings):
    """Настройки аутентификации."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SCRIPT_PATH: str = Field(
        default="protected/scriptV2.lua",
        description="Путь к скрипту",
    )
    LOADER_VERSION_FILE: str = Field(
        default="loader_version.json",
        description="Путь к файлу версии",
    )


class Settings(BaseSettings):
    """
    Основная конфигурация приложения.

    Агрегирует все подмодули настроек и предоставляет единый интерфейс.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Вложенные настройки — инициализируются через model_validator
    db: DatabaseSettings = None  # type: ignore
    llm: LLMSettings = None  # type: ignore
    telegram: TelegramSettings = None  # type: ignore
    cryptocloud: CryptoCloudSettings = None  # type: ignore
    tribute: TributeSettings = None  # type: ignore
    ml: MLSettings = None  # type: ignore
    auth: AuthSettings = None  # type: ignore

    # Application settings
    APP_NAME: str = Field(default="AdManager", description="Имя приложения")
    DEBUG: bool = Field(default=False, description="Режим отладки")
    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования")

    @model_validator(mode="after")
    def init_nested_settings(self) -> "Settings":
        """Инициализирует вложенные настройки."""
        if self.db is None:
            object.__setattr__(self, "db", DatabaseSettings())
        if self.llm is None:
            object.__setattr__(self, "llm", LLMSettings())
        if self.telegram is None:
            object.__setattr__(self, "telegram", TelegramSettings())
        if self.cryptocloud is None:
            object.__setattr__(self, "cryptocloud", CryptoCloudSettings())
        if self.tribute is None:
            object.__setattr__(self, "tribute", TributeSettings())
        if self.ml is None:
            object.__setattr__(self, "ml", MLSettings())
        if self.auth is None:
            object.__setattr__(self, "auth", AuthSettings())
        return self

    # Свойства для обратной совместимости
    @property
    def DATABASE_URL(self) -> str:
        return self.db.url

    @property
    def DB_USER(self) -> str:
        return self.db.USER

    @property
    def DB_PASS(self) -> str:
        return self.db.PASS

    @property
    def DB_NAME(self) -> str:
        return self.db.NAME

    @property
    def DB_HOST(self) -> str:
        return self.db.HOST

    @property
    def DB_PORT(self) -> int:
        return self.db.PORT

    @property
    def LLM_API_KEY(self) -> str:
        return self.llm.API_KEY

    @property
    def LLM_BASE_URL(self) -> str:
        return str(self.llm.BASE_URL)

    @property
    def LLM_MODEL(self) -> str:
        return self.llm.MODEL

    @property
    def LLM_TEMPERATURE(self) -> float:
        return self.llm.TEMPERATURE

    @property
    def LLM_MAX_TOKENS(self) -> int:
        return self.llm.MAX_TOKENS

    @property
    def BOT_TOKEN(self) -> str:
        return self.telegram.TOKEN

    @property
    def CRYPTOCLOUD_API_KEY(self) -> str:
        return self.cryptocloud.API_KEY

    @property
    def CRYPTOCLOUD_SHOP_ID(self) -> str:
        return self.cryptocloud.SHOP_ID

    @property
    def CRYPTOCLOUD_SECRET(self) -> str:
        return self.cryptocloud.SECRET

    @property
    def TRIBUTE_API_KEY(self) -> str:
        return self.tribute.API_KEY

    @property
    def RULES_FILE(self) -> str:
        return self.ml.RULES_FILE

    @property
    def EXAMPLES_FILE(self) -> str:
        return self.ml.EXAMPLES_FILE

    @property
    def ML_MODEL_NAME(self) -> str:
        return self.ml.ML_MODEL_NAME

    @property
    def SIMILARITY_THRESHOLD(self) -> float:
        return self.ml.SIMILARITY_THRESHOLD

    @property
    def TOP_K_EXAMPLES(self) -> int:
        return self.ml.TOP_K_EXAMPLES

    @property
    def QDRANT_URL(self) -> str:
        return str(self.ml.QDRANT_URL)

    @property
    def QDRANT_COLLECTION(self) -> str:
        return self.ml.QDRANT_COLLECTION

    @property
    def SCRIPT_PATH(self) -> str:
        return self.auth.SCRIPT_PATH

    @property
    def LOADER_VERSION_FILE(self) -> str:
        return self.auth.LOADER_VERSION_FILE

    @model_validator(mode="after")
    def validate_files_exist(self) -> "Settings":
        """Проверяет существование критических файлов."""
        if not Path(self.SCRIPT_PATH).exists():
            logger.warning("Script file not found: %s", self.SCRIPT_PATH)

        if not Path(self.LOADER_VERSION_FILE).exists():
            logger.warning(
                "Loader version file not found: %s", self.LOADER_VERSION_FILE
            )

        return self

    def validate_secrets(self) -> list[str]:
        """
        Проверяет безопасность секретов.

        Returns:
            Список предупреждений о безопасности
        """
        warnings = []

        # Проверка слабых секретов
        weak_secrets = {
            "BOT_TOKEN": self.BOT_TOKEN,
            "LLM_API_KEY": self.LLM_API_KEY,
            "TRIBUTE_API_KEY": self.TRIBUTE_API_KEY,
        }

        for name, secret in weak_secrets.items():
            if len(secret) < 20:
                warnings.append(f"{name} слишком короткий")

            # Проверка на тестовые значения
            if secret.startswith("fake_") or secret.startswith("test_"):
                warnings.append(f"{name} использует тестовое значение")

        # Проверка пароля БД
        if self.DB_PASS in {"password", "postgres", "admin", "12345678"}:
            warnings.append("DB_PASS использует слабый пароль")

        if warnings:
            logger.warning("Security warnings: %s", "; ".join(warnings))

        return warnings


@lru_cache
def get_settings() -> Settings:
    """
    Возвращает кэшированные настройки.

    Использует lru_cache для производительности.
    """
    return Settings()


# Глобальный экземпляр настроек
settings: Settings = Settings()  # type: ignore[call-arg]


def generate_secure_secret(length: int = 32) -> str:
    """
    Генерирует криптографически стойкий секрет.

    Args:
        length: Длина секрета в байтах

    Returns:
        Hex-строка секрета
    """
    return secrets.token_hex(length)


def hash_secret(secret: str, salt: str = "") -> str:
    """
    Хеширует секрет с солью.

    Args:
        secret: Секрет для хеширования
        salt: Соль (по умолчанию пустая)

    Returns:
        SHA-256 хеш в hex формате
    """
    return hashlib.sha256(f"{salt}{secret}".encode()).hexdigest()
