from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import settings

pool = ConnectionPool(
    settings.database_url,
    min_size=1,
    max_size=5,
    open=False,
    timeout=5,
    kwargs={"row_factory": dict_row, "connect_timeout": 3},
)


@contextmanager
def tx():
    """Una petición, una transacción: se confirma al salir o se revierte con la excepción."""
    with pool.connection() as conexion, conexion.transaction():
        yield conexion
