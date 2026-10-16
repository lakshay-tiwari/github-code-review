from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "cortex-api"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Infrastructure defaults (Local Docker)
    POSTGRES_USER: str = "cortex"
    POSTGRES_PASSWORD: str = "cortex_dev_password"
    POSTGRES_DB: str = "cortex"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = (
        "postgresql+asyncpg://cortex:cortex_dev_password@localhost:5432/cortex"
    )

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    QDRANT_HOST: str = "localhost"
    QDRANT_HTTP_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_URL: str = "http://localhost:6333"

    NEO4J_HOST: str = "localhost"
    NEO4J_HTTP_PORT: int = 7474
    NEO4J_BOLT_PORT: int = 7687
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "cortex_dev_password"
    NEO4J_URI: str = "bolt://localhost:7687"


settings = Settings()
