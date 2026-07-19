from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    aws_region: str = "ap-southeast-1"
    s3_bucket: str

    binance_base_url: str = "https://api.binance.com"
    request_timeout: int = 10
    max_retries: int = 3

    raw_data_path: str = "data/raw"
    s3_raw_prefix: str = "raw"

    log_level: str = "INFO"


settings = Settings()
