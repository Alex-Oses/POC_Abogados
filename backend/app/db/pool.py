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


def abrir() -> None:
    """Abre el pool; uno cerrado no se reutiliza, así que se crea otro (varios arranques en pruebas)."""
    global pool
    if pool.closed and pool._opened:
        pool = _nuevo()
    pool.open(wait=True, timeout=5)


def cerrar() -> None:
    pool.close()


@contextmanager
def tx():
    """Una petición, una transacción: se confirma al salir o se revierte con la excepción."""
    with pool.connection() as conexion, conexion.transaction():
        yield conexion
