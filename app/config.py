from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    keycloak_server_url: str
    keycloak_realm_name: str
    keycloak_client_id: str
    keycloak_client_secret: str
    
    # Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()