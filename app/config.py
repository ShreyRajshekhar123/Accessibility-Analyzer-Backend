# backend/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
import os # Import os to check environment variables directly

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    MONGODB_URI: str
    MONGODB_DB_NAME: str
    FIREBASE_SERVICE_ACCOUNT_BASE64: Optional[str] = None
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://accessibility-analyzer-kappa.vercel.app"
    ] 
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache()
def get_settings() -> Settings:
    """
    Caches the settings object.
    """
    print("--- Debugging Settings Loading ---")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Does .env exist? {os.path.exists('.env')}")
    print(f"MONGODB_URI from os.getenv: '{os.getenv('MONGODB_URI')}'")
    print(f"MONGODB_DB_NAME from os.getenv: '{os.getenv('MONGODB_DB_NAME')}'")
    print(f"GEMINI_API_KEY from os.getenv: '{os.getenv('GEMINI_API_KEY')}'")
    print("---------------------------------")
    return Settings()

settings = get_settings()