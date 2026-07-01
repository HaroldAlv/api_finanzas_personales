from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # JWT Settings (Shared with API Gateway)
    JWT_SECRET_KEY: str = "SuperSecretKeyForPuntoKontableApiGateway2026!"  # Ideally overridden by env
    JWT_ALGORITHM: str = "HS256"
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./app/data/personal_finances.db"
    
    # AI Settings
    AI_PROVIDER: str = "openai"       # "openai" | "ollama" | "gemini"

    OPENAI_API_KEY: str = ""  # Set via .env or environment variable
    OPENAI_MODEL: str = "gpt-4o-mini"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llava"
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_API_KEY: str = ""  # Set via .env or environment variable

    # File Upload Settings
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "./app/data/uploads"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
