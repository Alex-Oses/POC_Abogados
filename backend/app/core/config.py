from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    entorno: str = "desarrollo"
    log_level: str = "INFO"

    database_url: str = "postgresql://postgres:postgres@127.0.0.1:5432/icat"

    # U-17 y U-18
    session_horas: int = 1
    session_horas_max: int = 12
    sesiones_max: int = 3

    limite_intentos_login: int = 10
    ventana_intentos_seg: int = 300

    # U-21: admin local de desarrollo. Vacío = no se siembra.
    admin_email: str = ""
    admin_password: str = ""

    # Documentos: original cifrado con Fernet (0004). Sin clave no se admite subida.
    storage_dir: str = "storage"
    storage_key: str = ""
    max_upload_mb: int = 20

    # OCR (0001): PaddleOCR-VL por Ollama. OCR_MOCK=1 prueba sin modelo.
    ocr_mock: bool = False
    ollama_url: str = "http://localhost:11434"
    ocr_model: str = "hf.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF:latest"
    contraste_minimo: int = 80
    ocr_mock_delay: float = 0  # segundos por lectura simulada (pruebas de la cola)
    # Cola de OCR (0017): hilos del worker (1 = una página a la vez) y sondeo del NDJSON.
    ocr_workers: int = 1
    ocr_sondeo_seg: float = 1.0

    # Presidio (0006, docs/presidio.md): `md` es el equilibrio medido.
    spacy_model: str = "es_core_news_md"

    # Entrada por SharePoint (Microsoft Graph). Sin las cuatro primeras no se activa.
    sharepoint_tenant_id: str = ""
    sharepoint_client_id: str = ""
    sharepoint_client_secret: str = ""
    sharepoint_drive_id: str = ""  # biblioteca de documentos (GET /sites/{id}/drives)
    sharepoint_carpeta: str = "Entrada"  # dentro, una carpeta por persona
    sharepoint_sondeo_seg: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
