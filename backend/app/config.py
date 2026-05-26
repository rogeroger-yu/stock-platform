from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Stock Strategy Platform"
    debug: bool = False
    database_url: str = "sqlite:///./data/stock.db"
    data_dir: str = "./data"
    akshare_timeout: int = 30

    model_config = {"env_prefix": "STOCK_"}


settings = Settings()
