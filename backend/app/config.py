from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    app_name: str = "Stock Strategy Platform"
    debug: bool = False
    database_url: str = "sqlite:///./data/stock.db"
    data_dir: str = "./data"
    akshare_timeout: int = 30

    model_config = {"env_prefix": "STOCK_"}


def get_database_url() -> str:
    """Get database URL, ensuring data directory exists."""
    url = settings.database_url
    if url.startswith("sqlite"):
        # Extract path and ensure directory exists
        db_path = url.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    return url


settings = Settings()
