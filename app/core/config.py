from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # JWT Settings (Shared with API Gateway)
    JWT_SECRET_KEY: str = "SuperSecretKeyForPuntoKontableApiGateway2026!"  # Ideally overridden by env
    JWT_ALGORITHM: str = "HS256"
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///../data/personal_finances.db"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
