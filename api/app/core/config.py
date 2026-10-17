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
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str | None = "redis://localhost:6379/1"
    CELERY_TASK_DEFAULT_QUEUE: str = "cortex_default"

    QDRANT_HOST: str = "localhost"
    QDRANT_HTTP_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_NAME: str = "cortex_code_chunks"
    QDRANT_API_KEY: str | None = None
    QDRANT_PREFER_GRPC: bool = False


    NEO4J_HOST: str = "localhost"
    NEO4J_HTTP_PORT: int = 7474
    NEO4J_BOLT_PORT: int = 7687
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "cortex_dev_password"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50


    # Authentication (Clerk)
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: str = ""
    CLERK_ISSUER: str = ""
    CLERK_JWKS_URL: str = ""
    CLERK_AUTHORIZED_PARTY: str = ""
    CLERK_AUDIENCE: str = ""
    CLERK_PEM_PUBLIC_KEY: str = ""

    # LLM Configuration (Phase 3C)
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.2

    # Embedding Configuration (Phase 3C)
    EMBEDDING_PROVIDER: str = "sentence-transformers"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384


    @property
    def clerk_effective_issuer(self) -> str:
        """Derive the effective Clerk issuer URL."""
        if self.CLERK_ISSUER:
            return self.CLERK_ISSUER.rstrip("/")

        pub_key = self.CLERK_PUBLISHABLE_KEY or self.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
        if pub_key and ("pk_test_" in pub_key or "pk_live_" in pub_key):
            try:
                import base64

                b64_part = pub_key.split("_", 2)[-1]
                padded = b64_part + "=" * (-len(b64_part) % 4)
                domain = base64.b64decode(padded).decode("utf-8").rstrip("$")
                return f"https://{domain}"
            except Exception:
                pass

        # Fallback to default dev instance if configured in web/.env.local
        return "https://stunning-bobcat-41.clerk.accounts.dev"

    @property
    def clerk_effective_jwks_url(self) -> str:
        """Derive the effective Clerk JWKS URL."""
        if self.CLERK_JWKS_URL:
            return self.CLERK_JWKS_URL
        issuer = self.clerk_effective_issuer
        if issuer:
            return f"{issuer.rstrip('/')}/.well-known/jwks.json"
        return ""


settings = Settings()

