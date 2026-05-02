import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # General
    SECRET_KEY = os.environ.get("SECRET_KEY", "qf-admin-super-secret-key-2024")
    DEBUG = os.environ.get("DEBUG", "True") == "True"

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "qf-jwt-secret-key-2024")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REMEMBER_ME_EXPIRES = timedelta(days=30)

    # Password Reset Token Expiry
    PASSWORD_RESET_TOKEN_EXPIRES = timedelta(hours=1)

    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
