from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class IdentificarToken(BaseHTTPMiddleware):
    """Solo extrae el token. Quién puede qué se decide en `api/deps.py`."""

    async def dispatch(self, request: Request, call_next):
        cabecera = request.headers.get("authorization", "")
        esquema, _, token = cabecera.partition(" ")
        request.state.token = token if esquema.lower() == "bearer" and token else None
        return await call_next(request)
