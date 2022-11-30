from pydantic import BaseSettings


class Settings(BaseSettings):
    log_level: str = "INFO"
    enable_json_logging: bool = False
    model_path: str = "./worker.py"


settings = Settings()
