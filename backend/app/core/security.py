import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import settings

_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


def ahora() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    sal = secrets.token_bytes(16)
    clave = hashlib.scrypt(password.encode("utf-8"), salt=sal, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${sal.hex()}${clave.hex()}"


def verify_password(password: str, guardado: str | None) -> bool:
    if not guardado:
        return False
    try:
        algoritmo, n, r, p, sal, clave = guardado.split("$")
        if algoritmo != "scrypt":
            return False
        calculada = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(sal),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(clave)),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calculada.hex(), clave)


def nuevo_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def expira_sesion(creado_en: datetime, referencia: datetime | None = None) -> datetime:
    """Renovación deslizante con techo absoluto de 12 h desde que nació la sesión."""
    referencia = referencia or ahora()
    return min(
        referencia + timedelta(hours=settings.session_horas),
        creado_en + timedelta(hours=settings.session_horas_max),
    )
