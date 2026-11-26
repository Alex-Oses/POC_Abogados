"""Ficheros del expediente en disco. El original y los reescaneos van cifrados (0004)."""

import hashlib
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.errors import AppError


def _fernet() -> Fernet:
    if not settings.storage_key:
        raise AppError("STORAGE_SIN_CLAVE", "Falta STORAGE_KEY en la configuración", 500)
    return Fernet(settings.storage_key.encode())


def id_clave() -> str:
    """Identificador de la clave (nunca el material): huella corta del valor."""
    return "fernet:" + hashlib.sha256(settings.storage_key.encode()).hexdigest()[:12]


def ruta(*partes: str) -> Path:
    return Path(settings.storage_dir).joinpath(*partes)


def guardar(relativa: str, datos: bytes, cifrar: bool = True) -> None:
    destino = ruta(relativa)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(destino.suffix + ".tmp")
    temporal.write_bytes(_fernet().encrypt(datos) if cifrar else datos)
    os.replace(temporal, destino)  # atómico: nunca queda un fichero a medias


def leer(relativa: str, cifrado: bool = True) -> bytes:
    origen = ruta(relativa)
    if not origen.exists():
        raise AppError("FICHERO_NO_ENCONTRADO", "El fichero no existe", 404)
    datos = origen.read_bytes()
    if not cifrado:
        return datos
    try:
        return _fernet().decrypt(datos)
    except InvalidToken as error:
        raise AppError("FICHERO_ILEGIBLE", "No se puede descifrar el fichero", 500) from error


def existe(relativa: str) -> bool:
    return ruta(relativa).exists()
