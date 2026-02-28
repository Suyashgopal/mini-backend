"""
Configuration settings for the Flask application
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""

    # ---------------------------------------------------
    # Core App
    # ---------------------------------------------------
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "dev-secret-key-change-in-production"
    )

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URI",
        "sqlite:///ocr_compliance.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---------------------------------------------------
    # Upload Settings
    # ---------------------------------------------------
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")

    MAX_CONTENT_LENGTH = int(
        os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
    )

    ALLOWED_EXTENSIONS = {
        "png", "jpg", "jpeg", "pdf", "tiff", "bmp"
    }

    # ---------------------------------------------------
    # OCR ENGINE PRIORITY
    # ---------------------------------------------------
    # Primary Engine
    OCR_PRIMARY_ENGINE = os.getenv(
        "OCR_PRIMARY_ENGINE",
        "ollama"
    )

    # Fallback Engine
    OCR_FALLBACK_ENGINE = os.getenv(
        "OCR_FALLBACK_ENGINE",
        "tesseract"
    )

    # ---------------------------------------------------
    # Ollama Configuration
    # ---------------------------------------------------
    OLLAMA_ENABLED = os.getenv(
        "OLLAMA_ENABLED",
        "true"
    ).lower() == "true"

    OLLAMA_ENDPOINT = os.getenv(
        "OLLAMA_ENDPOINT",
        "http://localhost:11434"
    )

    OLLAMA_MODEL = os.getenv(
        "OLLAMA_MODEL",
        "glm-ocr:latest"
    )

    OLLAMA_TIMEOUT = int(
        os.getenv("OLLAMA_TIMEOUT", "30")
    )

    # ---------------------------------------------------
    # Tesseract Configuration
    # ---------------------------------------------------
    TESSERACT_CMD = os.getenv("TESSERACT_CMD")

    # ---------------------------------------------------
    # Offline Mode
    # ---------------------------------------------------
    OFFLINE_MODE = os.getenv(
        "OFFLINE_MODE",
        "false"
    ).lower() == "true"


# =====================================================
# Environment Configurations
# =====================================================

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

    # Force secure secret in production
    SECRET_KEY = os.getenv("SECRET_KEY")


class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///test_ocr_compliance.db"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}