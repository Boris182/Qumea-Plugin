from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # ---- App ----
    app_name: str = "Qumea Plugin"
    app_description: str = "Middleware zwischen Qumea und Ascom TelecareIP"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    token_url: str = "/login"
    host: str = "0.0.0.0"
    port: int = 8000

    # ---- Logging ----
    log_level: str = "DEBUG"
    log_dir: str = "data/logs"
    log_file: str = "app.log"
    log_max_bytes: int = 1_000_000
    log_backup_count: int = 5

    

    # ---- Database ----
    db_path: str = "data/database/app.db"

    # ---- JWT ----
    jwt_alg: str = "HS256"
    jwt_expire_min: int = 60

    # ---- Secrets via Environment ----
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    ssh_username: str | None = None
    ssh_password: str | None = None


def get_settings() -> Settings:
    return Settings()
