import os
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.core.config import settings
from app.core.security import hash_password
from app.main import app

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_TEST_URL"), reason="sin DATABASE_TEST_URL"
)

CLAVE = "una-clave-larga-123"


def _crear_usuario(rol: str) -> str:
    email = f"prueba-{uuid4().hex[:10]}@icat.local"
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conexion:
        fila = conexion.execute(
            "INSERT INTO usuarios (email, nombre, password_hash) "
            "VALUES (%s, 'Prueba', %s) RETURNING id",
            (email, hash_password(CLAVE)),
        ).fetchone()
        conexion.execute(
            "INSERT INTO usuarios_roles (usuario_id, rol) VALUES (%s, %s)",
            (fila["id"], rol),
        )
    return email


def _borrar_usuario(email: str) -> None:
    with psycopg.connect(settings.database_url) as conexion:
        conexion.execute("DELETE FROM usuarios WHERE email = %s", (email,))


@pytest.fixture()
def revisor():
    email = _crear_usuario("revisor")
    yield email
    _borrar_usuario(email)


@pytest.fixture()
def admin():
    email = _crear_usuario("admin")
    yield email
    _borrar_usuario(email)


@pytest.fixture(scope="session")
def cliente():
    with TestClient(app) as c:
        yield c


def _login(cliente: TestClient, email: str) -> str:
    respuesta = cliente.post(
        "/api/v1/user/login", json={"email": email, "password": CLAVE}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["access_token"]


def test_login_me_y_logout(cliente, revisor):
    token = _login(cliente, revisor)
    cabecera = {"Authorization": f"Bearer {token}"}

    yo = cliente.get("/api/v1/user/me", headers=cabecera)
    assert yo.status_code == 200
    assert yo.json()["roles"] == ["revisor"]

    assert cliente.post("/api/v1/user/logout", headers=cabecera).status_code == 204
    assert cliente.get("/api/v1/user/me", headers=cabecera).status_code == 401


def test_cuarta_sesion_desaloja_la_mas_antigua(cliente, revisor):
    tokens = [_login(cliente, revisor) for _ in range(4)]
    assert cliente.get(
        "/api/v1/user/me", headers={"Authorization": f"Bearer {tokens[0]}"}
    ).status_code == 401
    assert cliente.get(
        "/api/v1/user/me", headers={"Authorization": f"Bearer {tokens[3]}"}
    ).status_code == 200


def test_revisor_no_entra_en_administracion(cliente, revisor):
    token = _login(cliente, revisor)
    respuesta = cliente.get(
        "/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert respuesta.status_code == 403


def test_admin_cambia_roles_y_revoca_sesiones(cliente, revisor, admin):
    token_admin = _login(cliente, admin)
    cabecera_admin = {"Authorization": f"Bearer {token_admin}"}
    token_revisor = _login(cliente, revisor)
    cabecera_revisor = {"Authorization": f"Bearer {token_revisor}"}

    listado = cliente.get("/api/v1/admin/users", headers=cabecera_admin)
    assert listado.status_code == 200
    usuario = next(u for u in listado.json()["items"] if u["email"] == revisor)

    cambio = cliente.patch(
        f"/api/v1/admin/users/{usuario['id']}",
        headers=cabecera_admin,
        json={"roles": ["transcriptor"]},
    )
    assert cambio.status_code == 200
    assert cambio.json()["roles"] == ["transcriptor"]

    # U-09: cambiar roles revoca las sesiones abiertas.
    assert cliente.get("/api/v1/user/me", headers=cabecera_revisor).status_code == 401

    assert (
        cliente.delete(
            f"/api/v1/admin/users/{usuario['id']}/sessions", headers=cabecera_admin
        ).status_code
        == 204
    )
