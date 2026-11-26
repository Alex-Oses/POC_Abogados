"""Da de alta (o actualiza) un usuario local mientras no haya SSO (decisión 0012).

Uso, desde la carpeta POC_Abogados:
  backend/.venv/bin/python scripts/crear_usuario.py correo@icat.cat "Nombre" "Apellidos" transcriptor revisor

Roles: transcriptor, revisor, admin (uno o varios). Genera una contraseña aleatoria y la muestra
una sola vez; no se guarda en ningún log. Si el correo ya existe, cambia nombre, roles y contraseña.
"""

import os
import secrets
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)  # la configuración lee .env de la carpeta actual: funciona se lance desde donde se lance

import psycopg  # noqa: E402

from app.core.config import settings  # noqa: E402  (lee backend/.env)
from app.core.security import hash_password  # noqa: E402

ROLES = {"transcriptor", "revisor", "admin"}


def main() -> None:
    if len(sys.argv) < 5 or not set(sys.argv[4:]) <= ROLES or "@" not in sys.argv[1]:
        sys.exit(__doc__)
    email, nombre, apellidos, roles = sys.argv[1].lower(), sys.argv[2], sys.argv[3], sorted(set(sys.argv[4:]))
    clave = secrets.token_urlsafe(12)
    with psycopg.connect(settings.database_url) as c:
        uid = c.execute(
            "INSERT INTO usuarios (email, nombre, apellidos, password_hash, estado) "
            "VALUES (%s, %s, %s, %s, 'activo') "
            "ON CONFLICT (lower(email)) DO UPDATE SET nombre = EXCLUDED.nombre, "
            "apellidos = EXCLUDED.apellidos, password_hash = EXCLUDED.password_hash, estado = 'activo' "
            "RETURNING id", (email, nombre, apellidos, hash_password(clave))).fetchone()[0]
        c.execute("DELETE FROM usuarios_roles WHERE usuario_id = %s", (uid,))
        for rol in roles:
            c.execute("INSERT INTO usuarios_roles (usuario_id, rol) VALUES (%s, %s)", (uid, rol))
    print(f"Usuario listo: {email} · {nombre} {apellidos} · roles: {', '.join(roles)}")
    print(f"Contraseña inicial (apúntala, no se vuelve a mostrar): {clave}")


if __name__ == "__main__":
    main()
