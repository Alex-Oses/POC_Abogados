from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

COOKIE = "icat_token"


class IdentificarToken(BaseHTTPMiddleware):
    """Solo extrae el token. Quién puede qué se decide en `api/deps.py`."""

    async def dispatch(self, request: Request, call_next):
        cabecera = request.headers.get("authorization", "")
        esquema, _, token = cabecera.partition(" ")
        token = token if esquema.lower() == "bearer" and token else None
        # Cookie HttpOnly del login: la usan <img> y el visor del original, que no mandan cabecera.
        request.state.token = token or request.cookies.get(COOKIE)
        return await call_next(request)
