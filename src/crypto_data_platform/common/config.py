from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    aws_region: str = "ap-southeast-1"
    s3_bucket: str
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
