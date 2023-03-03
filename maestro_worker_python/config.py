from pydantic import BaseSettings


class Settings(BaseSettings):
    log_level: str = "INFO"
    enable_json_logging: bool = False
    model_path: str = "./worker.py"
    sentry_dsn: str = None
    sentry_traces_sample_rate: float = 1.0


settings = Settings()
