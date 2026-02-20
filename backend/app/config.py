from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://giinscore:giinscore_dev@localhost:5432/giinscore"
    cors_origins: str = "http://localhost:3000"
    kokkai_api_rate_limit: float = 1.0
    kokkai_api_base_url: str = "https://kokkai.ndl.go.jp/api"
    data_dir: str = "/data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
