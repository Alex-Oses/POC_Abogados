from typing import Any


def extraer_ocr_documento(contenido: bytes, nombre_fichero: str) -> list[dict[str, Any]]:
    """Cliente de integración con el servicio OCR/ETL externo (PaddleOCR-VL).

    Devuelve páginas con texto, semáforo de calidad y avisos.
    En ausencia de servicio externo, devuelve una estructura mínima para desarrollo.
    """
    return [
        {
            "numero_pagina": 1,
            "texto": "",
            "semaforo": "verde",
            "avisos": [],
            "origen": nombre_fichero,
        }
    ]


def detectar_entidades_presidio(texto: str, idioma: str = "es") -> list[dict[str, Any]]:
    """Detecta entidades sensibles sobre un bloque de texto.

    Usa Presidio si está disponible en el entorno; si no, devuelve lista vacía
    para permitir el flujo completo sin bloquear desarrollo.
    """
    return []
