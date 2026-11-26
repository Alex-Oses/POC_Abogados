from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from starlette.requests import Request

from app.core.config import settings
from app.core.errors import AppError

_intentos: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"


def limitar_login(request: Request) -> None:
    """Techo por IP y ventana, en memoria. Un worker; ver nota en la estructura aceptada."""
    ip = _ip(request)
    instante = monotonic()
    with _lock:
        cola = _intentos[ip]
        while cola and instante - cola[0] > settings.ventana_intentos_seg:
            cola.popleft()
        if len(cola) >= settings.limite_intentos_login:
            raise AppError("RATE_LIMITED", "Demasiados intentos; espera unos minutos", 429)
        cola.append(instante)
        # shortcut: el mapa de IPs es por proceso; se vacía a lo bruto si crece sin control.
        if len(_intentos) > 10_000:
            _intentos.clear()


def limpiar_login(request: Request) -> None:
    with _lock:
        _intentos.pop(_ip(request), None)
