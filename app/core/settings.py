from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Connection strings used for all instances of the application
    redis_url: str = "redis://localhost:6379/0"
    backend_url: str = "http://localhost:8080"

    # Adjust as needed
    policy_file_path: str = "config/policies.yaml"

    # Header name used to identify the client in incoming requests
    client_id_header: str = "X-API-Key"

    prometheus_enabled: bool = True

    # Log level for the application, can be set to DEBUG, INFO, WARNING, ERROR, or CRITICAL
    log_level: str = "INFO"

    excluded_paths: set[str] = {"/health", "/metrics"}

    model_config = {"env_prefix": "LIMITR_"}


settings = Settings()
