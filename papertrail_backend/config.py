"""
Configuration module for PaperTrail backend.
Loads environment variables and provides centralized configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the papertrail_backend directory
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(env_path)


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Application configuration class."""
    
    # Sarvam Vision API
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    SARVAM_VISION_LANGUAGE: str = os.getenv("SARVAM_VISION_LANGUAGE", "en-IN")
    SARVAM_VISION_OUTPUT_FORMAT: str = os.getenv("SARVAM_VISION_OUTPUT_FORMAT", "md")
    SARVAM_VISION_TIMEOUT: int = int(os.getenv("SARVAM_VISION_TIMEOUT", "240"))
    SARVAM_VISION_POLL_INTERVAL: float = float(os.getenv("SARVAM_VISION_POLL_INTERVAL", "3"))
    
    # Google Gemini API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # MongoDB
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "papertrail_db")
    
    # Collections
    CIVIL_RECORDS_COLLECTION: str = "civil_records_department"
    CITIZEN_SERVICES_COLLECTION: str = "citizen_services_department"
    AUDIT_LOGS_COLLECTION: str = "audit_logs"
    
    # File Upload
    DEFAULT_UPLOAD_DIR = BASE_DIR / "uploads"
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", str(DEFAULT_UPLOAD_DIR))
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg", "tiff", "bmp", "webp", "pdf"}
    
    # OCR Confidence Threshold
    CONFIDENCE_THRESHOLD: float = 0.75
    
    @staticmethod
    def validate_config() -> None:
        """Validate that all required configuration values are set."""
        if not Config.SARVAM_API_KEY:
            raise ValueError("SARVAM_API_KEY is not set in environment variables")
        if not Config.MONGO_URI:
            raise ValueError("MONGO_URI is not set in environment variables")
        
        # Ensure upload folder exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


config = Config()
