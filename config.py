import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")

    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "patient_case_db")

    _password = quote_plus(MYSQL_PASSWORD)
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{_password}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "documents")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_DOC_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

    TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
    POPPLER_PATH = os.getenv("POPPLER_PATH", "")

    AI_PROVIDER = os.getenv("AI_PROVIDER", "none")
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_API_URL = os.getenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")
    AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
