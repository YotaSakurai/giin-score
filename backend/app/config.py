from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""
    cors_origins: str = "http://localhost:3000"
    kokkai_api_rate_limit: float = 1.0
    kokkai_api_base_url: str = "https://kokkai.ndl.go.jp/api"
    data_dir: str = "/data"
    discord_webhook_url: str = ""
    admin_token: str = ""  # 管理画面認証トークン（環境変数 ADMIN_TOKEN で設定）

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
