import os
import secrets
from pathlib import Path

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MINIO_LOCAL_DIR = DATA_DIR / "minio_encrypted_storage"
DB_PATH = DATA_DIR / "auditcontabil.db"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MINIO_LOCAL_DIR, exist_ok=True)


class Settings(BaseSettings):
    APP_NAME: str = "AuditContábil AI"
    APP_VERSION: str = "2.0.0-Playbook-Full"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "auditcontabil-iso27001-jwt-secret-key-2026-br-sp-lgpd"
    )
    # Chave Mestra KEK (Key Encryption Key) de 256 bits (64 hex chars = 32 bytes) para Envelope Encryption
    MASTER_KEK_HEX: str = os.getenv(
        "MASTER_KEK_HEX",
        "8f4b2e1a9c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f"
    )
    DEFAULT_TENANT_ID: str = "escritorio-piloto-01"
    DATA_CENTER_REGION: str = "São Paulo, Brasil (sa-east-1 / Hostinger SP - 100% LGPD)"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")
    MINIO_STORAGE_PATH: str = str(MINIO_LOCAL_DIR)

    class Config:
        case_sensitive = True


settings = Settings()
