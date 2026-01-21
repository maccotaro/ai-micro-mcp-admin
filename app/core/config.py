"""設定管理"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """アプリケーション設定"""

    # Application
    app_name: str = "AI Micro MCP Admin"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8004

    # Database
    database_url: str = "postgresql://postgres:password@host.docker.internal:5432/admindb"

    # Redis
    redis_url: str = "redis://:password@host.docker.internal:6379"

    # API Admin
    api_admin_url: str = "http://host.docker.internal:8003"

    # RAG Service (9-stage hybrid search pipeline)
    rag_service_url: str = "http://host.docker.internal:8010"

    # Ollama
    ollama_base_url: str = "http://host.docker.internal:11434"
    embedding_model: str = "embeddinggemma:300m"
    chat_model: str = "pakachan/elyza-llama3-8b:latest"

    # Vector Store
    collection_name: str = "admin_documents"
    chunk_size: int = 500
    chunk_overlap: int = 75
    similarity_threshold: float = 0.7

    # CORS
    cors_origins: List[str] = [
        "http://localhost:3003",
        "http://localhost:3000",
        "http://host.docker.internal:3003"
    ]

    # Authentication
    jwks_url: str = "http://host.docker.internal:8002/.well-known/jwks.json"
    jwt_algorithm: str = "RS256"
    jwt_audience: str = "fastapi-api"
    jwt_issuer: str = "https://auth.example.com"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
