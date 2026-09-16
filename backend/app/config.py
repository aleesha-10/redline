import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://redline:redline@localhost:5432/redline"
    )
    TTL_SECONDS: int = int(os.getenv("TTL_SECONDS", "604800"))  # 7 days default
    SIMILARITY_MODEL: str = os.getenv(
        "SIMILARITY_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    INDEX_DIR: str = os.getenv("INDEX_DIR", "data/index")
    PRODUCT_ID: str = "legal.contract.risk.v1"
    VERSION: str = "1.0.0"


settings = Settings()
