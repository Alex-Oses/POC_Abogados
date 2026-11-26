from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    entorno: str = "desarrollo"
    log_level: str = "INFO"

    database_url: str = "postgresql://postgres:postgres@localhost:5432/icat"

    # U-17 y U-18
    session_horas: int = 1
    session_horas_max: int = 12
    sesiones_max: int = 3

    limite_intentos_login: int = 10
    ventana_intentos_seg: int = 300

    # U-21: admin local de desarrollo. Vacío = no se siembra.
    admin_email: str = ""
    admin_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
