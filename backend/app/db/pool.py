from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import settings


def _nuevo() -> ConnectionPool:
    return ConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=10,  # el streaming del OCR y la cola usan conexiones aparte
        open=False,
        timeout=5,
        kwargs={"row_factory": dict_row, "connect_timeout": 3},
    )


pool = _nuevo()
_cerrado = False


def abrir() -> None:
    """Abre el pool; uno cerrado no se reutiliza, así que se crea otro (varios arranques en pruebas)."""
    global pool, _cerrado
    if _cerrado:
        pool, _cerrado = _nuevo(), False
    pool.open(wait=True, timeout=5)


def cerrar() -> None:
    global _cerrado
    pool.close()
    _cerrado = True


@contextmanager
def tx():
    """Una petición, una transacción: se confirma al salir o se revierte con la excepción."""
    with pool.connection() as conexion, conexion.transaction():
        yield conexion
