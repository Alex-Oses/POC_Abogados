from fastapi.testclient import TestClient

from app.db.queries import SQL
from app.main import app

# Sin `with` no se ejecuta el lifespan: sirve para comprobar lo que no toca la BD.
cliente = TestClient(app)


def test_sin_token_es_401_antes_de_la_bd():
    respuesta = cliente.get("/api/v1/user/me")
    assert respuesta.status_code == 401
    assert respuesta.json() == {
        "error": {
            "code": "SESSION_NOT_FOUND",
            "message": "La sesión no existe o ha caducado",
        }
    }


def test_health_sin_bd_es_503():
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 503
    assert respuesta.json()["bd"] is False


def test_todas_las_consultas_estan_cargadas():
    esperadas = {
        "usuario_por_email",
        "sesion_por_token",
        "crear_sesion",
        "desalojar_sesiones",
        "tocar_sesion",
        "revocar_sesion",
        "revocar_sesiones_usuario",
        "actualizar_password",
        "password_hash_por_id",
        "listar_usuarios",
        "usuario_por_id",
        "actualizar_usuario",
        "borrar_roles",
        "agregar_rol",
        "sembrar_admin",
        "insertar",
    }
    assert esperadas <= set(SQL)
