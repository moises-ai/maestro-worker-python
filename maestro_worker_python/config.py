from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_level: str = "INFO"
    enable_json_logging: bool = False
    model_path: str = "./worker.py"
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 1.0
    sentry_errors_sample_rate: float = 1.0
    environment: str = "production"
    # Feeds /health and Sentry release/tags for the serving artifact.
    worker_name: str | None = None
    worker_version: str | None = None


settings = Settings()
