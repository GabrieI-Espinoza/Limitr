from pydantic import BaseModel


# Defines application settings
class Settings(BaseModel):
    redis_url: str = "redis://localhost:6379/0"
    policy_file_path: str = "config/policies.yaml"
    client_id_header: str = "X-API-Key"  # Header name to identify clients
    prometheus_enabled: bool = True  # Whether to expose Prometheus metrics endpoint
    excluded_paths: set[str] = {"/health", "/metrics", "/docs", "/openapi.json"}


settings = Settings()
