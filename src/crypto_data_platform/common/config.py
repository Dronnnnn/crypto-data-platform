from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    aws_region: str = "ap-southeast-1"
    s3_bucket: str
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
