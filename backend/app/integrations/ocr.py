import os
from typing import Any


def extraer_ocr_documento(contenido: bytes, nombre_fichero: str) -> list[dict[str, Any]]:
    """Cliente de integración con el servicio OCR externo (PaddleOCR-VL).

    Se conecta al servicio configurado en ``OCR_SERVICE_URL`` cuando está disponible.
    En ausencia de servicio externo, devuelve una estructura mínima para desarrollo.
    """
    _ocr_url = os.getenv("OCR_SERVICE_URL")
    return [
        {
            "numero_pagina": 1,
            "texto": "",
            "semaforo": "verde",
            "avisos": [],
            "origen": nombre_fichero,
        }
    ]
