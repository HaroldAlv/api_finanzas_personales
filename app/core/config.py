from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # JWT Settings (Shared with API Gateway)
    JWT_SECRET_KEY: str = "SuperSecretKeyForPuntoKontableApiGateway2026!"  # Ideally overridden by env
    JWT_ALGORITHM: str = "HS256"
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///../data/personal_finances.db"
    
    # AI Settings
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_PROVIDER: str = "openai"       # "openai" | "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llava"

    # File Upload Settings
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "../data/uploads" # Keeping relative to db script
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
