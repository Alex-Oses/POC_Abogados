from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import errors as pg_errors
from psycopg_pool import PoolTimeout

from app.core.errors import AppError
from app.core.logging import log


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        return _error(exc.code, exc.message, exc.status)

    @app.exception_handler(RequestValidationError)
    async def validacion(request: Request, exc: RequestValidationError):
        primero = exc.errors()[0]
        campo = ".".join(str(p) for p in primero.get("loc", []) if p != "body")
        return _error("VALIDACION", f"Petición no válida: {campo} {primero.get('msg', '')}".strip(), 400)

    @app.exception_handler(pg_errors.UniqueViolation)
    async def duplicado(request: Request, exc: pg_errors.UniqueViolation):
        return _error("CONFLICTO", "El recurso ya existe", 409)

    @app.exception_handler(pg_errors.ForeignKeyViolation)
    async def referencia(request: Request, exc: pg_errors.ForeignKeyViolation):
        return _error("REFERENCIA_INVALIDA", "El recurso referenciado no existe", 400)

    @app.exception_handler(pg_errors.OperationalError)
    async def sin_bd(request: Request, exc: pg_errors.OperationalError):
        log.error("bd_no_disponible", extra={"detalle": str(exc).splitlines()[0]})
        return _error("BD_NO_DISPONIBLE", "La base de datos no está disponible", 503)

    @app.exception_handler(PoolTimeout)
    async def pool_agotado(request: Request, exc: PoolTimeout):
        log.error("pool_agotado")
        return _error("BD_NO_DISPONIBLE", "La base de datos no está disponible", 503)

    @app.exception_handler(Exception)
    async def interno(request: Request, exc: Exception):
        log.exception("error_interno")
        return _error("ERROR_INTERNO", "Fallo interno", 500)
