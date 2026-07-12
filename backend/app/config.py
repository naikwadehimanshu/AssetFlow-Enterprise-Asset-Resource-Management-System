import os

class Settings:
    PROJECT_NAME: str = "AssetFlow Backend API"
    PROJECT_VERSION: str = "1.0.0"
    
    # SQLite Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./assetflow.db")
    
    # Security Configurations (Mock key for development)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY_FOR_ASSETFLOW_ERP_1234567890_ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day expiration for convenience

settings = Settings()
