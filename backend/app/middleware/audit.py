from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import log, nuevo_request_id, request_id


class RegistroPeticiones(BaseHTTPMiddleware):
    """Una línea por petición. Nunca cuerpo, query ni datos personales."""

    async def dispatch(self, request: Request, call_next):
        identificador = request.headers.get("x-request-id") or nuevo_request_id()
        marcador = request_id.set(identificador)
        inicio = perf_counter()
        try:
            respuesta = await call_next(request)
        except Exception:
            log.exception(
                "peticion_error",
                extra={"metodo": request.method, "ruta": request.url.path},
            )
            request_id.reset(marcador)
            raise
        respuesta.headers["X-Request-ID"] = identificador
        log.info(
            "peticion",
            extra={
                "metodo": request.method,
                "ruta": request.url.path,
                "estado": respuesta.status_code,
                "ms": round((perf_counter() - inicio) * 1000, 1),
            },
        )
        request_id.reset(marcador)
        return respuesta
