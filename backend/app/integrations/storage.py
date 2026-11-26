import hashlib
import os
from pathlib import Path

BASE_STORAGE = Path(os.getenv("STORAGE_DIR", "./storage")).resolve()


def _dir_seguro(subcarpeta: str) -> Path:
    destino = BASE_STORAGE / subcarpeta
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def guardar_original(documento_id: str, contenido: bytes) -> tuple[Path, str]:
    """Guarda el fichero original en disco de forma atómica y devuelve (ruta, sha256)."""
    carpeta = _dir_seguro("originales")
    ruta = carpeta / f"{documento_id}.bin"
    tmp = carpeta / f".{documento_id}.tmp"
    tmp.write_bytes(contenido)
    tmp.replace(ruta)
    digest = hashlib.sha256(contenido).hexdigest()
    return ruta, digest


def leer_original(documento_id: str) -> bytes | None:
    ruta = _dir_seguro("originales") / f"{documento_id}.bin"
    if not ruta.exists():
        return None
    return ruta.read_bytes()


def guardar_pdf_exportado(documento_id: str, numero_version: int, pdf_bytes: bytes) -> tuple[Path, str]:
    """Guarda el PDF exportado sin sobrescribir versiones previas (escritura atómica)."""
    carpeta = _dir_seguro("exports")
    ruta = carpeta / f"{documento_id}_v{numero_version}.pdf"
    if not ruta.exists():
        tmp = carpeta / f".{documento_id}_v{numero_version}.tmp"
        tmp.write_bytes(pdf_bytes)
        tmp.replace(ruta)
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    return ruta, digest
