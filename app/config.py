# backend/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Database settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "accessibility_analyzer_db"

    # Firebase service account file path
    FIREBASE_SERVICE_ACCOUNT_PATH: str = "./app/firebase-service-account.json"

    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"] # Add your frontend URL(s)

    # Environment configuration
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()