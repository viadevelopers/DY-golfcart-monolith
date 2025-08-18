from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/golfcart"
    JWT_SECRET: str = "your-super-secret-key-for-access-tokens"
    JWT_REFRESH_SECRET: str = "your-super-secret-key-for-refresh-tokens"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # 7 days

    class Config:
        env_file = ".env"

settings = Settings()
