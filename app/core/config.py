import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _BASE_DIR / ".env"

class Settings(BaseSettings):
    # App Settings
    USER_FULL_NAME: str = "Harold Andrés Aguilar Beltrán"
    USER_ACCOUNT_NUMBER: str = "24103557076"

    # JWT Settings (Shared with API Gateway)
    JWT_SECRET_KEY: str = ""  # Set via .env
    JWT_ALGORITHM: str = "HS256"
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./app/data/personal_finances.db"
    
    # AI Settings
    AI_PROVIDER: str = "openai"       # "openai" | "ollama" | "gemini"

    OPENAI_API_KEY: str = ""  # Set via .env
    OPENAI_MODEL: str = "gpt-4o-mini"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llava"
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_API_KEY: str = ""  # Set via .env

    # File Upload Settings
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "./app/data/uploads"

    USE_MARKITDOWN: bool = True
    MARKITDOWN_MIN_CHARS: int = 50
    
    model_config = SettingsConfigDict(env_file=str(_ENV_PATH), env_file_encoding="utf-8", extra="ignore")

settings = Settings()
