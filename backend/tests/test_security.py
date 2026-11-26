from datetime import UTC, datetime, timedelta

from app.core.security import (
    expira_sesion,
    hash_password,
    hash_token,
    nuevo_token,
    verify_password,
)


def test_password_ida_y_vuelta():
    guardado = hash_password("una-clave-larga-123")
    assert guardado.startswith("scrypt$")
    assert verify_password("una-clave-larga-123", guardado)
    assert not verify_password("otra-clave-larga-123", guardado)


def test_password_guardado_corrupto_no_revienta():
    assert not verify_password("x", None)
    assert not verify_password("x", "basura")
    assert not verify_password("x", "bcrypt$1$2$3$4$5")


def test_token_es_aleatorio_y_su_hash_estable():
    a, b = nuevo_token(), nuevo_token()
    assert a != b
    assert hash_token(a) == hash_token(a)
    assert len(hash_token(a)) == 64


def test_renovacion_tiene_techo_de_doce_horas():
    creada = datetime.now(UTC) - timedelta(hours=11, minutes=30)
    # 1 h deslizante, pero no más de 12 h desde que nació.
    assert expira_sesion(creada) == creada + timedelta(hours=12)
