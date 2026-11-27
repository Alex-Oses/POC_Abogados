"""Cola de OCR en segundo plano (0017): hilos dentro del backend, sin Redis ni Celery.

La cola es la propia tabla `documentos`: `pendiente` con `metadatos_extras.ocr` y sin
`ocr.error`. Cada hilo toma el más antiguo con `FOR UPDATE SKIP LOCKED`.
"""

import threading

from app.core.config import settings
from app.core.logging import log
from app.db.pool import tx
from app.db.queries import SQL
from app.services import documents

_parar = threading.Event()
despertar = threading.Event()  # la subida lo activa para no esperar al siguiente sondeo
_hilos: list[threading.Thread] = []


def tomar() -> dict | None:
    with tx() as conexion:
        return conexion.execute(SQL["cola_tomar"]).fetchone()


def reanudar() -> list:
    """Devuelve a la cola lo que quedó en `ocr_procesando` (caída o reinicio)."""
    with tx() as conexion:
        conexion.execute(SQL["cola_huerfanos"])
        return [f["id"] for f in conexion.execute(SQL["cola_reanudar"]).fetchall()]


def _bucle(parar: threading.Event) -> None:
    while not parar.is_set():
        try:
            doc = tomar()
        except Exception:  # noqa: BLE001 - BD caída: se reintenta en el siguiente sondeo
            log.exception("cola_ocr_sin_bd")
            doc = None
        if doc:
            documents.procesar_documento(doc, parar.is_set)
            continue
        despertar.wait(2)
        despertar.clear()


def arrancar() -> None:
    global _parar
    if any(h.is_alive() for h in _hilos):  # ya en marcha (arranques anidados en pruebas)
        return
    _parar = threading.Event()  # nuevo: un hilo viejo que tarde en salir no revive
    reanudados = reanudar()
    if reanudados:
        log.info("cola_ocr_reanudada", extra={"detalle": len(reanudados)})
    for i in range(max(settings.ocr_workers, 1)):
        hilo = threading.Thread(target=_bucle, args=(_parar,), name=f"cola-ocr-{i}", daemon=True)
        hilo.start()
        _hilos.append(hilo)


def detener(espera: float = 5) -> None:
    """Para al terminar la página en curso; lo que quede a medias se reanuda al arrancar."""
    _parar.set()
    despertar.set()
    for hilo in _hilos:
        hilo.join(espera)
    _hilos.clear()
