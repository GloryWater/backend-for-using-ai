from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # игнорируем лишние переменные из .env
    )

    # --- Database ---
    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    DB_HOST: str = "db"
    DB_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # --- LLM ---
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL: str
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 200

    # --- Telegram ---
    BOT_TOKEN: str

    # --- CryptoCloud ---
    CRYPTOCLOUD_API_KEY: str = ""
    CRYPTOCLOUD_SHOP_ID: str = ""
    CRYPTOCLOUD_SECRET: str = ""

    # --- Tribute ---
    TRIBUTE_API_KEY: str

    # --- ML / Vector DB ---
    RULES_FILE: str = "src/AI/rules.xml"
    EXAMPLES_FILE: str = "src/AI/data.jsonl"
    ML_MODEL_NAME: str = "paraphrase-multilingual-MiniLM-L12-v2"
    SIMILARITY_THRESHOLD: float = 0.5
    TOP_K_EXAMPLES: int = 10
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_COLLECTION: str = "examples_collection"

    # --- Auth / Loader ---
    SCRIPT_PATH: str = "protected/scriptV2.lua"
    LOADER_VERSION_FILE: str = "loader_version.json"


settings = Settings()
