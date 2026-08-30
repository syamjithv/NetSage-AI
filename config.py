import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///netsage.db")
    AI_PROVIDER = os.getenv("AI_PROVIDER", "placeholder")
    AI_MODEL = os.getenv("AI_MODEL", "placeholder")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
